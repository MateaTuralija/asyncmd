# This file is part of asyncmd.
#
# asyncmd is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# asyncmd is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with asyncmd. If not, see <https://www.gnu.org/licenses/>.
import os
import logging
import numpy as np


from ..trajectory.trajectory import Trajectory
from .mdconfig import MDP


logger = logging.getLogger(__name__)


def nstout_from_mdp(mdp: MDP, traj_type: str = "TRR") -> int:
    """Get lowest output frequency for gromacs trajectories from MDP class."""
    if traj_type.upper() == "TRR":
        keys = ["nstxout", "nstvout", "nstfout"]
    elif traj_type.upper() == "XTC":
        keys = ["nstxout-compressed", "nstxtcout"]
    else:
        raise ValueError("traj_type must be one of 'TRR' or 'XTC'.")

    vals = []
    for k in keys:
        try:
            # need to check for 0 (== no output!) in case somone puts the
            # defaults (or reads an mdout.mdp where gmx lists all the defaults)
            v = mdp[k]
            if v == 0:
                v = float("inf")
            vals += [v]
        except KeyError:
            # not set, defaults to 0, so we ignore it
            pass

    nstout = min(vals, default=None)
    if (nstout is None) or (nstout == float("inf")):
        raise ValueError("The MDP you passed results in no trajectory output.")
    return nstout


def get_all_traj_parts(folder: str, deffnm: str,
                       traj_type: str = "TRR") -> "list[Trajectory]":
    """Find and return a list of trajectory parts produced by a GmxEngine."""
    # NOTE: this assumes all files/parts are ther, i.e. nothing was deleted
    #       we just check for the highest number and also assume the tpr exists
    ending = traj_type.lower()
    traj_files = get_all_file_parts(folder=folder, deffnm=deffnm,
                                    file_ending=ending)
    trajs = [Trajectory(trajectory_file=traj_file,
                        structure_file=os.path.join(folder, f"{deffnm}.tpr")
                        )
             for traj_file in traj_files]
    return trajs


def get_all_file_parts(folder: str, deffnm: str, file_ending: str) -> "list[str]":
    """Find and return all files with given ending produced by GmxEngine."""
    # NOTE: this assumes all files/parts are ther, i.e. nothing was deleted
    #       we just check for the highest number and also assume they exist
    def partnum_suffix(num):
        # construct gromacs num part suffix from simulation_part
        num_suffix = str(num)
        while len(num_suffix) < 4:
            num_suffix = "0" + num_suffix
        num_suffix = ".part" + num_suffix
        return num_suffix

    if not file_ending.startswith("."):
        file_ending = "." + file_ending
    content = os.listdir(folder)
    filtered = [f for f in content
                if (f.endswith(file_ending) and f.startswith(f"{deffnm}.part"))
                ]
    partnums = [int(f.lstrip(f"{deffnm}.part").rstrip(file_ending))
                for f in filtered]
    # max_num = 0 will result in us returning an empty list
    max_num = np.max(partnums) if len(partnums) > 0 else 0
    parts = [os.path.join(folder, f"{deffnm}{partnum_suffix(num)}{file_ending}")
             for num in range(1, max_num+1)]
    return parts


def ensure_mdp_options(mdp: MDP, genvel: str = "no", continuation: str = "yes") -> MDP:
    """
    Ensure that some commonly used mdp options have the given values.

    Modifies the MDP inplace but also returns it.
    """
    try:
        # make sure we do not generate velocities with gromacs
        genvel_test = mdp["gen-vel"]
    except KeyError:
        logger.info(f"Setting 'gen-vel = {genvel}' in mdp.")
        mdp["gen-vel"] = genvel
    else:
        if genvel_test[0] != genvel:
            logger.warning(f"Setting 'gen-vel = {genvel}' in mdp "
                           + f"(was '{genvel_test[0]}').")
            mdp["gen-vel"] = genvel
    try:
        # TODO/FIXME: this could also be 'unconstrained-start'!
        #             however already the gmx v4.6.3 docs say
        #            "continuation: formerly know as 'unconstrained-start'"
        #            so I think we can ignore that for now?!
        continuation_test = mdp["continuation"]
    except KeyError:
        logger.info(f"Setting 'continuation = {continuation}' in mdp.")
        mdp["continuation"] = continuation
    else:
        if continuation_test[0] != continuation:
            logger.warning(f"Setting 'continuation = {continuation}' in mdp "
                           + f"(was '{continuation_test[0]}').")
            mdp["continuation"] = continuation

    return mdp
