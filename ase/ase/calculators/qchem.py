"""This module defines an ASE interface to NWchem
http://www.nwchem-sw.org/
"""

import os

import numpy as np

from warnings import warn
from ase.atoms import Atoms
from ase.units import Hartree, Bohr
from ase.io.qchem import write_qchem, read_qchem_opt_output
from ase.calculators.calculator import FileIOCalculator, Parameters, ReadError


class QChem(FileIOCalculator):
    implemented_properties = ['optimization']
    command = 'qchem PREFIX.in > PREFIX.out'
    #-----------------------------------------
    jobtype     = {'optimization' : 'OPT'}
    exchange    = {'B3LYP'  : 'B3LYP'}
    correlation = {'B3LYP'  : 'B3LYP'}
    basis       = {'STO-3G' : 'STO-3G',
                   '3-21G'  : '3-21G',
                   '6-31G'  : '6-31G',
                   '6-31G*' : '6-31G*'}
    #-----------------------------------------

    default_parameters = dict(
        xc='LDA',
        task='optimization',
        geometry=None,
        symmetry=False,
        basis='STO-3G',
        thresh=12,
        scf_convergence=8,
        maxfile=128,
        mem_static = 40,
        mem_total = 400)

    def __init__(self, restart=None, ignore_bad_restart_file=False,
                 label='qchem', atoms=None, **kwargs):
        """Construct NWchem-calculator object."""
        FileIOCalculator.__init__(self, restart, ignore_bad_restart_file,
                                  label, atoms, **kwargs)

    def set(self, **kwargs):
        changed_parameters = FileIOCalculator.set(self, **kwargs)
        if changed_parameters:
            self.reset()

    def check_state(self, atoms):
        system_changes = FileIOCalculator.check_state(self, atoms)
        # Ignore unit cell and boundary conditions:
        if 'cell' in system_changes:
            system_changes.remove('cell')
        if 'pbc' in system_changes:
            system_changes.remove('pbc')
        return system_changes

    def write_input(self, atoms=None, properties=None, system_changes=None):
        FileIOCalculator.write_input(self, atoms, properties, system_changes)
        p = self.parameters
        p.write(self.label + '.ase')
        f = open(self.label + '.in', 'w')
        write_qchem(f, atoms, p.geometry)

        f.write("$rem\n")
        f.write("JOBTYPE          " + self.jobtype[p.task]   + "\n")
        f.write("EXCHANGE         " + self.exchange[p.xc]    + "\n")
        f.write("CORRELATION      " + self.correlation[p.xc] + "\n")
        f.write("BASIS            " + self.basis[p.basis]    + "\n")
        f.write("SYMMETRY         " + str(p.symmetry)        + "\n")
        f.write("THRESH           " + str(p.thresh)          + "\n")
        f.write("SCF_CONVERGENCE  " + str(p.scf_convergence) + "\n")
        f.write("MAX_SUB_FILE_NUM " + str(p.maxfile)         + "\n")
        f.write("MEM_STATIC       " + str(p.mem_static)      + "\n")
        f.write("MEM_TOTAL        " + str(p.mem_total)       + "\n")
        f.write("$end\n")

    def read_output(self):
        p = self.parameters
        if (p.task == "optimization"):
            return read_qchem_opt_output(self.label + ".out")

    def run_opt(self, atoms):
        self.write_input(atoms)
        if self.command is None:
            raise RuntimeError('Please set $%s environment variable ' %
                               ('ASE_' + self.name.upper() + '_COMMAND') +
                               'or supply the command keyword')
        command = self.command.replace('PREFIX', self.prefix)
        olddir = os.getcwd()
        try:
            os.chdir(self.directory)
            errorcode = subprocess.call(command, shell=True)
        finally:
            os.chdir(olddir)

        if errorcode:
            raise RuntimeError('%s returned an error: %d' %
                               (self.name, errorcode))
        mol, E = self.read_output()
        return mol, E

