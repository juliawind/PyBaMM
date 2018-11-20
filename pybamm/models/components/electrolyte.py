#
# Equations for the electrolyte
#
from __future__ import absolute_import, division
from __future__ import print_function, unicode_literals

import numpy as np


class Electrolyte(object):
    """Equations for the electrolyte."""

    def set_simulation(self, param, operators, mesh):
        """
        Assign simulation-specific objects as attributes.

        Parameters
        ----------
        param : :class:`pybamm.parameters.Parameters` instance
            The parameters of the simulation
        operators : :class:`pybamm.operators.Operators` instance
            The spatial operators.
        mesh : :class:`pybamm.mesh.Mesh` instance
            The spatial and temporal discretisation.
        """
        self.param = param
        self.operators = operators
        self.mesh = mesh

    def initial_conditions(self):
        """Calculates initial conditions for variables in the electrolyte.

        Returns
        -------
        dict
            The initial conditions
        """
        c0 = self.param.c0 * np.ones_like(self.mesh.xc)
        en0 = self.param.U_Pb(self.param.c0) * np.ones_like(self.mesh.xcn)
        ep0 = self.param.U_PbO2(self.param.c0) * np.ones_like(self.mesh.xcp)

        return {"c": c0, "en": en0, "ep": ep0}

    def cation_conservation(self, c, j, flux_bcs):
        """Conservation of cations.

        Parameters
        ----------
        c : array_like, shape (n,)
            The electrolyte concentration.
        j : array_like, shape (n,)
            The interfacial current density.
        flux_bcs : 2-tuple of array_like, shape (1,)
            Flux at the boundaries (Neumann BC).

        Returns
        -------
        dcdt : array_like, shape (n,)
            The time derivative of c.

        """
        # Calculate internal flux
        N_internal = -self.operators["xc"].grad(c)

        # Add boundary conditions (Neumann)
        flux_bc_left, flux_bc_right = flux_bcs
        N = np.concatenate([flux_bc_left, N_internal, flux_bc_right])

        # Calculate time derivative
        dcdt = -self.operators["xc"].div(N) + self.param.s * j

        return dcdt

    def bcs_cation_flux(self):
        """Flux boundary conditions for the cation conservation equation.

        Returns
        -------
        2-tuple of array_like, shape(1,)
            The boundary conditions.

        """
        flux_bc_left = np.array([0])
        flux_bc_right = np.array([0])
        return (flux_bc_left, flux_bc_right)

    def current_conservation(self, domain, c, e, j, current_bcs):
        """The 1D diffusion equation.

        Parameters
        ----------
        param : pybamm.parameters.Parameter() instance
            The parameters of the simulation
        variables : 2-tuple (c, e) of array_like, shape (n,)
            The concentration, and potential difference.
        operators : pybamm.operators.Operators() instance
            The spatial operators.
        j : array_like, shape (n,)
            Interfacial current density.
        current_bcs : 2-tuple of array_like, shape (1,)
            Flux at the boundaries (Neumann BC).

        Returns
        -------
        dedt : array_like, shape (n,)
            The time derivative of the potential.

        """
        # Calculate current density
        i = self.macinnes(domain, c, e, current_bcs)

        # Calculate time derivative
        if domain == "xcn":
            gamma_dl = self.param.gamma_dl_n
        elif domain == "xcp":
            gamma_dl = self.param.gamma_dl_p

        dedt = 1 / gamma_dl * (self.operators[domain].div(i) - j)

        return dedt

    def macinnes(self, domain, c, e, current_bcs):
        """MacInnes equation for the electrolyte current density.

        Parameters
        ----------
        domain : string
            The domain in which to calculate the electrolyte current density.
        c : array_like, shape (n,)
            The electrolyte concentration.
        e : array_like, shape (n,)
            The potential difference.
        current_bcs : 2-tuple of array_like, shape (1,)
            Flux at the boundaries (Neumann BC).

        Returns
        -------
        i : array_like, shape (n+1,)
            The current density.
        """
        operators = self.operators[domain]
        kappa_over_c = 1
        kappa = 1

        # Calculate inner current
        i_inner = kappa_over_c * operators.grad(c) + kappa * operators.grad(e)

        # Add boundary conditions
        lbc, rbc = current_bcs
        i = np.concatenate([lbc, i_inner, rbc])

        return i

    def bcs_current(self, domain, t):
        """Boundary conditions for the current conservation equation.

        Returns
        -------
        2-tuple of array_like, shape(1,)
            The boundary conditions.

        """
        if domain == "xcn":
            current_bc_left = np.array([0])
            current_bc_right = np.array([self.param.icell(t)])
        elif domain == "xcp":
            current_bc_left = np.array([self.param.icell(t)])
            current_bc_right = np.array([0])
        return (current_bc_left, current_bc_right)
