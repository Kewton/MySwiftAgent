"""Registration workflow for Job Generator V2.

This package contains the RegistrationWorkflow and its sub-workflows:
- RegistrationWorkflow: Main workflow orchestrating master and job registration
- MasterManagerSubWorkflow: Creates InterfaceMaster, TaskMaster, JobMaster
- JobRegistrarSubWorkflow: Registers Job and JobQueue entries

Issue #342 Phase D.1: Registration workflow implementation.
"""

from aiagent.langgraph.jobGeneratorV2.workflows.registration.job_registrar import (
    JobRegistrarSubWorkflow,
)
from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
    MasterManagerSubWorkflow,
)
from aiagent.langgraph.jobGeneratorV2.workflows.registration.workflow import (
    RegistrationWorkflow,
)

__all__ = [
    "RegistrationWorkflow",
    "MasterManagerSubWorkflow",
    "JobRegistrarSubWorkflow",
]
