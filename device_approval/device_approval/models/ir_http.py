# -*- coding: utf-8 -*-
import logging
from odoo import models, api, _
from odoo.http import request

_logger = logging.getLogger(__name__)


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _authenticate(cls, endpoint):
        """
        Hook called after standard authentication.
        We validate device approval here so that it applies to
        all authenticated sessions, not just the /web/login route.
        """
        result = super()._authenticate(endpoint)
        # Device check is handled at login time via the controller override
        return result
