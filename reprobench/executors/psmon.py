import subprocess
from loguru import logger
from pathlib import Path
from psmon.main import run

from reprobench.core.bases import Step
from reprobench.core.db import db, Run, RunStatistic


class PsmonExecutor(Step):
    def run(self, context):
        tool = context["tool"]
        limits = context["limits"]
        tool.pre_run(context)

        cwd = context["run"].directory
        out_file = (Path(cwd) / "run.out").open("wb")
        err_file = (Path(cwd) / "run.err").open("wb")

        context["run"].status = Run.RUNNING
        context["run"].save()

        cmd = tool.cmdline(context)
        logger.debug(f"Running {cwd}")
        logger.trace(cmd)

        stats = run(
            cmd,
            cwd=cwd,
            stdout=out_file,
            stderr=err_file,
            cpu_time_limit=limits["time"],
            wall_time_limit=limits["time"] + 15,
            memory_limit=limits["memory"],
            freq=15,
        )

        logger.debug(f"Finished {cwd}")
        logger.debug(stats)

        context["run"].status = Run.DONE
        context["run"].return_code = stats["return_code"]

        if stats["error"] == TimeoutError:
            context["run"].verdict = Run.TIMEOUT
        elif stats["error"] == MemoryError:
            context["run"].verdict = Run.MEMOUT
        elif stats["error"] or stats["return_code"] != 0:
            context["run"].verdict = Run.RUNTIME_ERR
        else:
            context["run"].verdict = Run.SUCCESS

        context["run"].save()

        RunStatistic.create(
            run=context["run"], key=RunStatistic.WALL_TIME, value=stats["wall_time"]
        )
        RunStatistic.create(
            run=context["run"], key=RunStatistic.CPU_TIME, value=stats["cpu_time"]
        )
        RunStatistic.create(
            run=context["run"], key=RunStatistic.MEM_USAGE, value=stats["max_memory"]
        )

        tool.post_run(context)
