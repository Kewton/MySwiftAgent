// src/services/graphai.ts
import { GraphAI } from "graphai";
import { readGraphaiData } from "@receptron/test_utils";
import * as packages from "@graphai/agents";
import { tokenBoundStringsAgent } from "@graphai/token_bound_string_agent";
import { fileReadAgent, fileWriteAgent, pathUtilsAgent } from "@graphai/vanilla_node_agents";
import dotenv from 'dotenv';
import { secretsManager } from './secretsManager.js';
import { settings } from '../config/settings.js';

dotenv.config();

const MODEL_BASE_PATH = process.env.MODEL_BASE_PATH || settings.MODEL_BASE_PATH;

// Type definitions for GraphAI data structures
interface GraphNodeConfig {
  agent: string;
  params?: Record<string, unknown>;
  inputs?: Record<string, unknown>;
  [key: string]: unknown;
}

interface GraphData {
  nodes: Record<string, GraphNodeConfig>;
  [key: string]: unknown;
}

// GraphAI response type with detailed error information
export interface GraphAIResponse {
  results: Record<string, unknown>;
  errors: Record<string, { message: string; stack?: string }>;
  logs: Array<{
    nodeId: string;
    state: string;
    errorMessage?: string;
    startTime?: number;
    endTime?: number;
    retryCount?: number;
  }>;
}

const agents = {
  ...packages,
  tokenBoundStringsAgent,
  fileReadAgent,
  fileWriteAgent,
  pathUtilsAgent,
};

// Remove unwanted properties like `__esModule` and `module.exports`
const agents_2 = Object.fromEntries(
  Object.entries(agents).filter(([key]) => key !== "__esModule" && key !== "module.exports")
);

/**
 * YAMLデータ内のagentパラメータにシークレットを注入
 *
 * 対応agent:
 * - openAIAgent → OPENAI_API_KEY
 * - anthropicAgent → ANTHROPIC_API_KEY
 * - geminiAgent → GOOGLE_API_KEY
 * - groqAgent → GROQ_API_KEY
 * - replicateAgent → REPLICATE_API_KEY
 *
 * 並行リクエスト対応：各リクエストが独立したgraph_dataオブジェクトを持つため安全
 */
async function injectSecretsToGraphData(graph_data: GraphData, project?: string): Promise<void> {
  // Agent名とシークレット名のマッピング
  const secretsMap: Record<string, string> = {
    'openAIAgent': 'OPENAI_API_KEY',
    'anthropicAgent': 'ANTHROPIC_API_KEY',
    'geminiAgent': 'GOOGLE_API_KEY',
    'groqAgent': 'GROQ_API_KEY',
    'replicateAgent': 'REPLICATE_API_KEY',
  };

  for (const [nodeId, nodeConfig] of Object.entries(graph_data.nodes) as [string, GraphNodeConfig][]) {
    const agentName = nodeConfig.agent;
    const secretKey = secretsMap[agentName];

    if (secretKey) {
      try {
        // MyVaultから取得（優先度: MyVault → 環境変数 → エラー）
        const apiKey = await secretsManager.getSecret(secretKey, project);

        // paramsが存在しない場合は初期化
        nodeConfig.params = nodeConfig.params || {};

        // APIキーを注入
        nodeConfig.params.apiKey = apiKey;

        console.log(`✓ Injected '${secretKey}' into node '${nodeId}' (agent: ${agentName}, project: ${project || 'default'})`);
      } catch (error) {
        console.warn(`⚠️ Failed to inject secret '${secretKey}' for agent '${agentName}' in node '${nodeId}': ${error}`);
        // シークレット取得失敗時もエラーを投げない
        // agent内部で環境変数フォールバックが動作する可能性があるため
      }
    }
  }
}

/**
 * GraphAIを実行（リクエスト毎に独立したgraph_dataオブジェクトを使用）
 *
 * @returns GraphAIResponse - 全ノードの結果、エラー情報、実行ログを含む
 */
export const runGraphAI = async (user_input: string, model_name: string, project?: string): Promise<GraphAIResponse> => {
  console.log("Available agents:", Object.keys(agents_2));

  const modelpath = MODEL_BASE_PATH + model_name + ".yml";

  // ① リクエスト毎に新しいgraph_dataオブジェクトを生成（並行リクエスト対応）
  const graph_data = readGraphaiData(modelpath);

  // ② このリクエスト専用のgraph_dataにシークレットを注入
  await injectSecretsToGraphData(graph_data, project);

  console.log("Graph data:", graph_data);
  // console.log(JSON.stringify(graph_data, null, 2));

  // ③ このリクエスト専用のGraphAIインスタンスを生成
  const graph = new GraphAI(graph_data, agents_2);
  graph.injectValue("source", user_input);

  let results: Record<string, unknown> = {};
  let runError: Error | null = null;

  // ④ 実行（中間ノードも含めて全結果を取得、エラーをキャッチ）
  try {
    results = await graph.run(true);
  } catch (error) {
    console.error("Error during GraphAI run:", error);
    runError = error instanceof Error ? error : new Error(String(error));
    // エラーが発生してもログ情報は取得できる可能性があるため、処理を継続
  }

  // ⑤ エラー情報を取得（run()がエラーを投げた場合でも取得可能）
  const errorMap = graph.errors();
  const errors = Object.fromEntries(
    Object.entries(errorMap).map(([id, err]) => [
      id,
      {
        message: err.message,
        stack: err.stack
      }
    ])
  );

  // ⑥ 実行ログを取得（タイムアウト、リトライ情報を含む）
  const transactionLogs = graph.transactionLogs();

  // 各ノードの最終状態のみを取得（重複を除去）
  const nodeLogMap = new Map<string, typeof transactionLogs[0]>();
  for (const log of transactionLogs) {
    // 後のログで上書きすることで、最終状態のみが残る
    nodeLogMap.set(log.nodeId, log);
  }

  const logs = Array.from(nodeLogMap.values()).map(log => ({
    nodeId: log.nodeId,
    state: log.state,
    errorMessage: log.errorMessage,
    startTime: log.startTime,
    endTime: log.endTime,
    retryCount: log.retryCount,
  }));

  // ⑦ エラー情報を詳細にログ出力
  if (Object.keys(errors).length > 0) {
    console.error("=== GraphAI Execution Errors ===");
    for (const [nodeId, error] of Object.entries(errors)) {
      const nodeConfig = graph_data.nodes[nodeId];
      const agentName = nodeConfig?.agent || 'unknown';

      console.error(`ERROR: <-- NodeId: ${nodeId}, Agent: ${agentName}`);
      console.error(`ERROR: Message: ${error.message}`);

      // fetchAgent固有のエラー詳細を表示
      if (agentName === 'fetchAgent' && nodeConfig?.inputs) {
        const inputs = nodeConfig.inputs as Record<string, unknown>;
        console.error(`ERROR: URL: ${inputs.url || 'not specified'}`);
        console.error(`ERROR: Method: ${inputs.method || 'GET'}`);
      }

      if (error.stack) {
        console.error(`ERROR: Stack Trace:`);
        console.error(error.stack);
      }
      console.error(`ERROR: -->`);
    }
  }

  console.log("GraphAI Results:", results);
  console.log("GraphAI Errors:", errors);
  console.log("GraphAI Logs:", logs);

  // ⑦ run()で例外が発生し、かつerrors()やlogs()にも情報がない場合は例外を再スロー
  if (runError && Object.keys(errors).length === 0 && logs.length === 0) {
    throw runError;
  }

  return {
    results,
    errors,
    logs,
  };
};

/**
 * GraphAIテスト実行
 *
 * @returns GraphAIResponse - 全ノードの結果、エラー情報、実行ログを含む
 */
export const testGraphAI = async (project?: string): Promise<GraphAIResponse> => {
  console.log("Available agents:", Object.keys(agents_2));

  const graph_data = readGraphaiData(MODEL_BASE_PATH + "test.yml");

  await injectSecretsToGraphData(graph_data, project);

  console.log("Graph data:", graph_data);
  console.log(JSON.stringify(graph_data, null, 2));

  const graph = new GraphAI(graph_data, agents_2);
  graph.injectValue("source", "ドラゴンボールの作者をメールで送信してね");

  let results: Record<string, unknown> = {};
  let runError: Error | null = null;

  // 中間ノードも含めて全結果を取得、エラーをキャッチ
  try {
    results = await graph.run(true);
  } catch (error) {
    console.error("Error during GraphAI run:", error);
    runError = error instanceof Error ? error : new Error(String(error));
    // エラーが発生してもログ情報は取得できる可能性があるため、処理を継続
  }

  // エラー情報を取得（run()がエラーを投げた場合でも取得可能）
  const errorMap = graph.errors();
  const errors = Object.fromEntries(
    Object.entries(errorMap).map(([id, err]) => [
      id,
      {
        message: err.message,
        stack: err.stack
      }
    ])
  );

  // 実行ログを取得
  const transactionLogs = graph.transactionLogs();

  // 各ノードの最終状態のみを取得（重複を除去）
  const nodeLogMap = new Map<string, typeof transactionLogs[0]>();
  for (const log of transactionLogs) {
    // 後のログで上書きすることで、最終状態のみが残る
    nodeLogMap.set(log.nodeId, log);
  }

  const logs = Array.from(nodeLogMap.values()).map(log => ({
    nodeId: log.nodeId,
    state: log.state,
    errorMessage: log.errorMessage,
    startTime: log.startTime,
    endTime: log.endTime,
    retryCount: log.retryCount,
  }));

  // エラー情報を詳細にログ出力
  if (Object.keys(errors).length > 0) {
    console.error("=== GraphAI Execution Errors ===");
    for (const [nodeId, error] of Object.entries(errors)) {
      const nodeConfig = graph_data.nodes[nodeId];
      const agentName = nodeConfig?.agent || 'unknown';

      console.error(`ERROR: <-- NodeId: ${nodeId}, Agent: ${agentName}`);
      console.error(`ERROR: Message: ${error.message}`);

      // fetchAgent固有のエラー詳細を表示
      if (agentName === 'fetchAgent' && nodeConfig?.inputs) {
        const inputs = nodeConfig.inputs as Record<string, unknown>;
        console.error(`ERROR: URL: ${inputs.url || 'not specified'}`);
        console.error(`ERROR: Method: ${inputs.method || 'GET'}`);
      }

      if (error.stack) {
        console.error(`ERROR: Stack Trace:`);
        console.error(error.stack);
      }
      console.error(`ERROR: -->`);
    }
  }

  console.log("GraphAI Results:", results);
  console.log("GraphAI Errors:", errors);
  console.log("GraphAI Logs:", logs);

  // run()で例外が発生し、かつerrors()やlogs()にも情報がない場合は例外を再スロー
  if (runError && Object.keys(errors).length === 0 && logs.length === 0) {
    throw runError;
  }

  return {
    results,
    errors,
    logs,
  };
};
