# avoid using pyslurm as it is an external dependence and is not portable as well
import os
import re
import sys
import time
import subprocess
from datetime import datetime

from subway.exceptions import SubwayException


class SlurmException(SubwayException):
    def __init__(self, message, code=90):
        super().__init__(message, code)


class SlurmValueError(SlurmException):
    def __init__(self, message, code=91):
        super().__init__(message, code)


class SlurmJob:
    def __init__(self, jobname=None, jobid=None, sacct="sacct"):
        self.sacct = sacct
        if (not jobname) and (not jobid):
            raise SlurmValueError("Must specify jobid or jobname")
        if jobid:
            self.jobid = jobid
        else:  # only jobname is defined (it is the user's responsibility to make sure that jobname is unique)
            self.jobid = self.get_jobid(jobname)
        self.jobinfo = self.get_jobinfo(self.jobid)
        self.jobname = self.jobinfo["JobName"]

    def get_jobid(self, jobname, tries=6):
        for i in range(tries):
            try:
                return self._get_jobid(jobname)
            except SlurmException as e:
                if e.code != 98 or i == tries - 1:
                    raise e
                else:
                    print(e.message, file=sys.stderr)
                    time.sleep(0.5)

    def _get_jobid(self, jobname):
        r = subprocess.run(
            [self.sacct, "--name=%s" % jobname, "--format=JobID%50,Jobname%50"],
            stdout=subprocess.PIPE,
        )
        rl = r.stdout.decode("utf-8").split("\n")
        # print(rl)# seconds after job submit, no line is expected with rl[2] = ""
        if len(rl) > 2 and rl[2]:
            jid = [s for s in rl[2].split(" ") if s][0].strip()
            return jid
        errmsg = "no job name is %s, you may need wait for a second" % jobname
        raise SlurmException(errmsg, code=98)

    def get_jobinfo(self, jobid):
        """

        :param jobid:
        :return: jobinfo: dict, {'User': 'linuxuser', 'JobID': '4500', 'JobName': 'uuid',
                                'Partition': 'general', 'State': 'COMPLETED', 'Timelimit': '365-00:00+',
                                'Start': '2020-02-23T10:05:55', 'End': '2020-02-23T10:06:15',
                                'Elapsed': '00:00:20', 'NNodes': '1', 'NCPUS': '2', 'NodeList': 'c7'}
        """
        # TODO: caution on "ValueError: time data 'Unknown' does not match format '%Y-%m-%dT%H:%M:%S'"
        r = subprocess.run(
            [
                self.sacct,
                "-j",
                jobid,
                "--format=User%30,JobID%50,Jobname%50,partition%20,state%20,time,start,end,elapsed,nnodes,ncpus,nodelist",
            ],
            stdout=subprocess.PIPE,
        )
        rl = r.stdout.decode("utf-8").split("\n")
        rl = [rl[0], rl[2]]
        rl = [s.strip() for s in rl if s.strip()]
        rll = [[s for s in l.split(" ") if s] for l in rl]
        assert len(rll[0]) == len(rll[1])
        info = {}
        for i, head in enumerate(rll[0]):
            info[head] = rll[1][i]
        info["Start_ob"] = datetime.strptime(info["Start"], "%Y-%m-%dT%H:%M:%S")
        info["Start_ts"] = info["Start_ob"].timestamp()
        if info.get("End", ""):
            info["End_ob"] = datetime.strptime(info["End"], "%Y-%m-%dT%H:%M:%S")
            info["End_ts"] = info["End_ob"].timestamp()
        return info


class SlurmTask:
    def __init__(
        self,
        sbatch="sbatch",
        scancel="scancel",
        shebang="#!/bin/bash",
        sbatch_path=None,
        sbatch_options=None,
        sbatch_commands=None,
    ):
        """

        :param sbatch: string, binary for sbatch
        :param sbatch: string, binary for scancel
        :param shebang: string, the #! line
        :param sbatch_path: string, sbatch script path
        :param sbatch_options: list of strings, such as "--job-name=uuid"
        :param sbatch_commands: list of strings, main command, such as "python test.py"
        """
        self.sbatch = sbatch
        self.scancel = scancel
        self.sbatch_path = sbatch_path
        self.shebang = shebang
        if not sbatch_commands:
            sbatch_commands = []
        self.sbatch_commands = sbatch_commands
        if not sbatch_options:
            sbatch_options = []
        self.sbatch_options = sbatch_options
        if not os.path.exists(sbatch_path):
            self._render_sbatch()
        self.jid = None

    def _render_sbatch(self):
        sbatch_string = self.shebang + "\n"
        for opt in self.sbatch_options:
            sbatch_string += "#SBATCH  " + opt + "\n"
        for line in self.sbatch_commands:
            sbatch_string += line + "\n"
        sbatch_string += "\n"
        with open(self.sbatch_path, "w") as f:
            f.writelines([sbatch_string])
        os.chmod(self.sbatch_path, 0o700)

    def submit(self):
        if not os.path.exists(self.sbatch_path):
            raise SlurmException("No sbatch file at %s" % self.sbatch_path, code=92)
        self.outerr = subprocess.run(
            [self.sbatch, self.sbatch_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def stdouterr(self):
        stdout = self.outerr.stdout
        stderr = self.outerr.stderr
        if stdout:
            stdout = stdout.decode("utf-8")
        if stderr:
            stderr = stderr.decode("utf-8")
        return stdout, stderr

    def jobid(self):
        if not self.jid:
            stdout, stderr = self.stdouterr()
            if stdout:
                l = re.search(r"Submitted batch job (\d.*)", stdout)
                self.jid = l.groups()[0]
                return self.jid
            raise SlurmException(
                "No stdout for sbatch submit, the err is %s" % stderr, code=93
            )
        else:
            return self.jid

    def cancel(self):
        self.jobid()
        r = subprocess.run(
            [self.scancel, self.jid], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        return r
