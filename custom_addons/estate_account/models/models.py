# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class estate_account(models.Model):
#     _name = 'estate_account.estate_account'
#     _description = 'estate_account.estate_account'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

from odoo import models, api,_,fields
from odoo.exceptions import UserError
from odoo import Command

class estate_account(models.Model):
    _inherit = "estate.property"

     #Overrides the 'action_sold' method to create an invoice when a property is sold.

    def action_sold(self):
        """Overrides 'action_sold' to create an invoice with two invoice lines when a property is sold."""
        
        # # Ensure a buyer exists before creating an invoice
        # if not self.buyer_id:
        #     raise UserError(_("A buyer must be assigned before selling the property."))

        # Compute invoice line values
        selling_price = self.selling_price
        service_fee = selling_price * 0.06  # 6% of selling price
        admin_fee = 100.00  # Fixed admin fee

        # Create the invoice
        invoice = self.env["account.move"].create({
            "partner_id": self.buyer_id.id,  # Buyer as the invoice recipient
            "move_type": "out_invoice",  # Customer Invoice
            "invoice_date": fields.Date.today(),
            "state": "draft",  # Initially in draft state
            "invoice_line_ids": [
                Command.create({
                    "name": f"{self.name}",
                    "quantity": 1,
                    "price_unit": service_fee,
                }),
                Command.create({
                    "name": "Administrative Fees",
                    "quantity": 1,
                    "price_unit": admin_fee,
                })
            ],
        })

        print(f"Invoice {invoice.id} created for Property {self.id}")  # Debugging Output

        # Call the parent method to finalize the sale
        return super().action_sold()