// src/services/graphai.ts
import { GraphAI } from "graphai";
import { readGraphaiData } from "@receptron/test_utils";
import * as packages from "@graphai/agents";
import { tokenBoundStringsAgent } from "@graphai/token_bound_string_agent";
import { fileReadAgent, fileWriteAgent, pathUtilsAgent } from "@graphai/vanilla_node_agents";
import dotenv from 'dotenv';

dotenv.config();

const MODEL_BASE_PATH = process.env.MODEL_BASE_PATH || "";

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

export const runGraphAI = async (user_input: string, model_name: string) => {
  console.log("Available agents:", Object.keys(agents_2));

  try {
    const modelpath = MODEL_BASE_PATH + model_name + ".yml";
    const graph_data = readGraphaiData(modelpath);

    console.log("Graph data:", graph_data);
    console.log(JSON.stringify(graph_data, null, 2));

    const graph = new GraphAI(graph_data, agents_2);
    graph.injectValue("source", user_input);

    const result = await graph.run();
    console.log("GraphAI Result:", result);
    return result;
  } catch (error) {
    console.error("Error during GraphAI instantiation or run:", error);
    throw error;
  }
};

export const testGraphAI = async () => {
  console.log("Available agents:", Object.keys(agents_2));

  try {
    const graph_data = readGraphaiData(MODEL_BASE_PATH + "test.yml");

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
