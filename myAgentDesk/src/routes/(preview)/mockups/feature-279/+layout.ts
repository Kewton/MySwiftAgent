import type { LayoutLoad } from './$types';
import mockData from './data/mock.json';

export const load: LayoutLoad = async () => {
	return {
		featureNumber: 279,
		...mockData
	};
};

export const prerender = true;
