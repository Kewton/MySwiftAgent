export interface RequirementState {
	data_source: string | null;
	process_description: string | null;
	output_format: string | null;
	schedule: string | null;
	completeness: number;
}

export interface JobResult {
	job_id: string;
	job_master_id: string;
	status: string;
	message: string;
}

export function createEmptyRequirements(): RequirementState {
	return {
		data_source: null,
		process_description: null,
		output_format: null,
		schedule: null,
		completeness: 0
	};
}
