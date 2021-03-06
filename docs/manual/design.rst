Design Philosophy
==================

|

- Keep everything

    Keep everything for later analysis, all inputs and outputs files,
    as well as submit scripts.
    It is worth noting that the common practice that only keep output files
    with file name as input parameters is not good enough and fail in many scenarios.

- Keep history

    To keep everything organized and easy for analysis, we keep all necessary informations
    for each job as a separate file ``history.json``.
    There is no need to directly access this file for normal user though.

- Organize tasks as trees

    An HPC project is a forest.
    Root jobs should develop children jobs when "converge condition" is not satisfied by check jobs.

- Manage projects with CLI interface

    From ``.subway`` directory to enhanced ``subway`` CLI utility,
    subway behaves somehow parallelling ``git``.

|

CLI utility
===========

.. _clioverview:

An overview
-------------

The CLI command ``subway`` is ready to use if subway is install by ``pip`` or ``python setup.py install``.
If the users cannot or don't want to install subway via setup system, the package still works as standalone one.
To enable CLI support in this case, one need to:

    .. code-block:: bash

        export SUBWAY_PATH=/abspath/for/subway/bin
        export PATH=$SUBWAY_PATH:$PATH
        export SUBWAY_PYTHON=pythonyoulike

And ``subway`` command in shell is read to go!

The power of CLI tool is illustrated below:

    .. code-block:: bash

        $ subway -V
        subway version: 0.0.1
        $ subway init
        the subway project has been successfully initialized in <current dir>
        $ subway config edit
        # edit config.json
        # copy executables into the project and write up entry_point py script as the monitor
        $ subway run
        # the whole project is then running nonstopped, following the config and entry_point engine
        $ subway query -j 134 info
        # check detailed info of job with jobid starts with 134
        $ subway query -s "checking_tso<datetime(2020,2,2)"
        # search all jobs whose checking time if before 02/02/2020
        $ subway query -s "executable_version<>1.0.0; state=running"
        # search all jobs whose executable version is not 1.0.0 and the job is running
        $ subway query -s "resource.memory_count<=128"
        # search all jobs whole resource requirement on memory is no greater than 128
        $ subway query tree
        # print the job tree in the terminal
        $ subway query root
        # print all root jobs


CLI commands
--------------

There are more possibilies of CLI ``subway`` to be explored. In summary, there are the following parts for subway CLI:

- ``subway init``: Init a subway project.

- ``subway run``: Run the subway project by entry point.

- ``subway config``: ``show`` or ``edit`` config of the subway project.

- ``subway query``: The most powerful interface on analysing jobs based on ``history.json``.

- ``subway debug``: Some useful shortcuts for debugging and quick testing.

It is worthing noting shortcuts such as ``subway r``, ``subway c`` also work.

Query interface
------------------

For ``subway q``, the most general query statement is by ``-s``, as we have seen in :ref:`overview <clioverview>`.

The statement follows ``-s`` is made of several equations, such as "state=pending; checking_tso<datetime(2020,2,2,20,2,20)".
These conditions separates with ";" and possible space. The sign supported include "=", ">", "<", ">=", "<=", "<>".

The last one means unequal. ">" and "<" sign has special meanings when list is involved. For example, ``subway q -s prev<["1", "2"]``
finds jobs whose prev attr is either 1 or 2. On the other hand ``subway q -s next>1`` finds jobs whose next attr (a list) include 1.

Subway will detect jobs satisfy all conditions at the same time. The attributes are with the same name as in ``history.json``.
The higher order attributes can be accessed with "." notation. For example, to query ``cpu_count`` in ``resource``, we can
use ``subway query -s "resource.cpu_count>2"``. For list element, one can treat the key as ``list_0`` and so on.

Beyond these attributes, there are also some special attribute query statement supports. These attrs ends with "_ts" are extended
to attrs with "_tso" where python datetime object is obtained and can be compared directly in the form as ``checking_tso<datetime(2020,2,2,20,2,20)``.


``subway query`` has other powerful short cuts beyond ``-s``.
``subway query tree`` print job trees of the subject.
``subway -j <jobid> input`` shows input for <jobid>. It is also handy that we only need to write down the very beginning part of a long jobid.
The full jobid can be automatically matched and used.
``subway -j <jobid> ending_time`` shows the ``ending_ts`` for <jobid> in human readable way instead of timestamp.

|


Relevant json files
======================

.. _config.json:

config.json
-------------

The reserved configuration keys include:

- ``inputs_dir``, ``outputs_dir``: str, relpath. The default directories for input files and output files. The job submission scripts are also recommended in ``inputs_dir`` with ``.sh`` suffix. (omitted is ok)

- ``check_inputs_dir``, ``check_outputs_dir``: str, relpath. The directories for check job inputs and outputs if there are any. These options can be omitted is check tasks don't go through submitter. (omitted is ok)

- ``entry_point``: str, relpath. The engine py script for monitoring tasks, default as ``main.py``.

- ``work_dir``: str, abspath. Dir path for this subway project. (omitted is ok)

- ``resource_limit``: Dict[str, Union[float, int]]. Keys end with ``_limit`` are treated as resource limitation. (omitted is ok)

- ``executable_version``, ``check_executable version``: str. Script versions for main and check executables. (omitted is ok)

- ``executable``: str, relpath. The binary path for main task. (omitted is ok)

- ``check_executable``: str, relpath. The binary path for check task. (omitted is ok)

- ``_py``: str. Abs path for preferred python binary.

-   ``_executable``: str. All keys end with executable are reserved.

- ``_version``: str. All keys end with version are reserved.

- ``_template``: str. All keys end with template are reserved.


Note all path above in config are relative path compared to ``work_dir``, which is the only absolute path.

There are also other keys used in different plugins as submitter and checker.

For example, :mod:`subway.plugins.sslurm` requires extra options, check plugin relavant documentations for more details:

- ``slurm_commands``, ``check_slurm_commands``: List[str]. Used in sbatch scripts, main commands.

- ``slurm_options``, ``check_slurm_options``: List[str]. Used in sbatch scripts, lines start with ``#SBATCH``.



.. _history.json:

history.json
---------------

Keys in ``history.json`` are jobids, for each job, there is an information dict, the common keys include:

- ``prev``: str. The parent job id. None for root jobs.

- ``next``: List[str]. The children job ids. ``[]`` for leaves jobs.

- ``state``: str. Job state, legal values include: pending, running, finished, aborted, checking, resolving, checked, frustrated, resolved, failed.

- ``creating_ts``: float. Timestamps when the task is created, start of pending state.

- ``beginning_ts``: float. Timestamps when the task is submitted by the submitter, separating pending and running state.

- ``finishing_ts``: float. Timestamps when the main task of the job is finished, separating running state and finished/aborted state.

- ``checking_ts``: float. Timestamps when the associate check task begins running, separating finished and checking state, or separating aborted and resolving state.

- ``ending_ts``: float. Timestamps when the associate check task is finished and all the stuff are over for given job, separating checking state and checked/frustrated state, or separating resolving state and resolved/failed state.

- ``resource``: Dict[str, Any]. Storage for extra informations on the job. The most important ones are keys ends with ``_count``, these attributes are used to limit total computation resources.

- ``assoc``: str. Associated job id for check task of the job. In general check task share the same item with main task.

- ``check_resource``: Dict[str, Any]. resource dict for check task.

- ``executable_version``, ``check_executable_version``: str. Version information for binaries involved in the job.

Again, for plugins, more attributes are expected.  For example, :mod:`subway.plugins.sslurm`  has extra attributes in history.

- ``beginning_real_ts``: float. Timestamps, when the job is begin running from slurm.


|

Checker - Submitter Architecture
=================================

.. _CSA:

Checker and Submitter
-----------------------

The main loop in entry_point of subway is just running checker and submitter again and again.

The responsibility for the checker is:

1. Check whether running jobs are finished or aborted or still running.

2. If they are finished/aborted, mark their states accordingly,  and generate inputs for associate check/resolve task and return task id and resource for the new check/resolve task.

3. Check whether checking/resolving jobs are checked(frustrated)/resolved(failed).

4. If they are checked/resolved, generate inputs for new job and return new jobs id and their resource and then mark their state accordinglu.

Step 1,2 of C transform jobs from running to finished/aborted. Step 3,4 of C transform jobs from checking/resolving to checked(frustrated)/resolved(failed).
The subtlety is the timing of marking job states. Checker first marks running jobs as finished or aborted and then go to step 2.
On the other hand, checker first generate new jobs and them marks jobs as checked(frustrated)/resolved(failed).

The responsibility for the submitter is:

1. Check whether there are some pending jobs.

2. If yes, submit them and then mark them as running jobs.

3. Check whether there are finished/aborted jobs.

4. If yes, submit them as associate check jobs and then mark them as checking/resolving jobs.


Throughout all the process, all items and state in :ref:`history.json` shall be carefully dealt with.


.. _dsss:

Double vs. Single Submitter
------------------------------

We call them DS and SS scheme for simplicity. The difference here is whether check task are managed by submitter.
Specifically, in the case of slurm submitter, the difference is whether check task is simple and time saving to run inside
entry_point main loop within python (SS), or check jobs are also time consuming and need to be run externally and submitted on slurm (DS).
Subway supports both scheme. And DS scheme is exactly described in :ref:`csa`.

For SS scheme, the responsibility for the checker is:

1. Check whether running jobs are finished or aborted or still running.

2. If they are finished/aborted, directly change their state to checking/resolving and do nothing else.

3. Find checking/resolving jobs.

4. Using check function insdie python to check the main outout and generate inputs for new job and return new jobs id and their resource, then change job states accordingly as checked(frustrated)/resolved(failed).


The responsibility for the submitter is:

1. Check whether there are some pending jobs.

2. If yes, submit them and then mark them as running jobs.

3. There is no finished/aborted job by design.

4. Submit nothing. (skipped by design)


As we can see, the above workflow parallels DS scheme so that they can share the same super class as the common abstractions.
Since only step 2 do real submission, compared to step 2,4 in DS scheme, that's why it is called single submitter scheme.


General workflow for plain C-S
---------------------------------

.. figure:: ../static/wf.svg
    :width: 100%
    :align: center
    :alt: alternate text
    :figclass: align-center

    Workflow for plain submitter(S) and checker(C).

In the above figure, all core methods within :class:`subway.framework.PlainSub` and :class:`subway.framework.PlainChk` are described.
The user can customize these methods as they like.

Besides submitter and checker in the main loop, one can also add processor before and after the main loop.
The processor will run all methods of its own from the arguments ``pipeline``. Eg, see :class:`subway.framework.PreProcessor`


Exceptions
==============

Table between exceptions and codes