# © 2022 - FactorLibre - Oscar Indias <oscar.indias@factorlibre.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    margin_tax = fields.Selection(
        string="Tax in product margin",
        selection=[("include", "Include"), ("exclude", "Exclude")],
        default="exclude",
        required=True,
    )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ir_config_sudo = self.env['ir.config_parameter'].sudo()
        margin_tax = ir_config_sudo.get_param(
            'product_standard_margin.margin_tax',  default="exclude")
        res.update(margin_tax=margin_tax)
        return res

    @api.multi
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        ir_config_sudo = self.env['ir.config_parameter'].sudo()
        ir_config_sudo.set_param(
            'product_standard_margin.margin_tax',
            self.margin_tax,
        )
