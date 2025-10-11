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
 */
export const runGraphAI = async (user_input: string, model_name: string, project?: string) => {
  console.log("Available agents:", Object.keys(agents_2));

  try {
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

    // ④ 実行（他のリクエストと競合しない）
    const result = await graph.run();
    console.log("GraphAI Result:", result);
    return result;
  } catch (error) {
    console.error("Error during GraphAI instantiation or run:", error);
    throw error;
  }
};

export const testGraphAI = async (project?: string) => {
  console.log("Available agents:", Object.keys(agents_2));

  try {
    const graph_data = readGraphaiData(MODEL_BASE_PATH + "test.yml");

    await injectSecretsToGraphData(graph_data, project);

    console.log("Graph data:", graph_data);
    console.log(JSON.stringify(graph_data, null, 2));

    const graph = new GraphAI(graph_data, agents_2);
    graph.injectValue("source", "ドラゴンボールの作者をメールで送信してね");

    const result = await graph.run();
    console.log("GraphAI Result:", result);
    return result;
  } catch (error) {
    console.error("Error during GraphAI instantiation or run:", error);
    throw error;
  }
};
