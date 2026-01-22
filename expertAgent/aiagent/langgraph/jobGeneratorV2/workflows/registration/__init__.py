"""Registration workflow for Job Generator V2.

This package contains the RegistrationWorkflow and its sub-workflows:
- RegistrationWorkflow: Main workflow orchestrating master and job registration
- MasterManagerSubWorkflow: Creates InterfaceMaster, TaskMaster, JobMaster
- JobRegistrarSubWorkflow: Registers Job and JobQueue entries

Issue #342 Phase D.1: Registration workflow implementation.
Issue #393: Added update_task_master_body_template_taskflow from task_master_utils.
"""

from aiagent.langgraph.jobGeneratorV2.workflows.registration.job_registrar import (
    JobRegistrarSubWorkflow,
)
from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
    MasterManagerSubWorkflow,
)
from aiagent.langgraph.jobGeneratorV2.workflows.registration.task_master_utils import (
    update_task_master_body_template_taskflow,
)
from aiagent.langgraph.jobGeneratorV2.workflows.registration.workflow import (
    RegistrationWorkflow,
)

__all__ = [
    "RegistrationWorkflow",
    "MasterManagerSubWorkflow",
    "JobRegistrarSubWorkflow",
    "update_task_master_body_template_taskflow",
]
