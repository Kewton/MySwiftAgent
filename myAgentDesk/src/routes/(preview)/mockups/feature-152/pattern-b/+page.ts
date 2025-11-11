import type { PageLoad } from './$types';
import mockData from '../data/mock.json';

export const load: PageLoad = async () => {
  return {
    candidates: mockData.candidates,
    feedbackScores: mockData.feedbackScores,
    metrics: mockData.metrics
  };
};
