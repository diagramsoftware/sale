# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import api, models


class sale_order(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def action_button_confirm(self):
        res = super(sale_order, self).action_button_confirm()

        if self.type_id.validate_automatically_picking and self.picking_ids:
            self.picking_ids[0].force_assign()
            detail_transfer_id = self.picking_ids[0].transfer_details()
            self.env['stock.transfer_details'].browse(
                detail_transfer_id).do_detailed_transfer()

        if self.type_id.journal_id and self.type_id.validate_automatically_invoice:

            # Creamos factura desde albaran
            if self.type_id.validate_automatically_picking and self.picking_ids:
                self.env['stock.invoice.onshipping'].with_context(active_ids=self.picking_ids.ids).create({}).open_invoice()
                invoice_id = self.picking_ids[0].invoice_id.id

            # La creamos desde el pedido
            else:
                invoice_id = self.action_invoice_create()

            self.env['account.invoice'].browse(invoice_id).signal_workflow('invoice_open')
            if self.type_id.payment_journal_id:
                inv = self.env['account.invoice'].browse(invoice_id)
                if inv:
                    account_voucher_obj = self.env['account.voucher']
                    amount = inv.type in (
                        'out_refund', 'in_refund') and -inv.residual or inv.residual
                    voucher = account_voucher_obj.create({
                        "name": "",
                        "amount": amount,
                        "journal_id": self.type_id.payment_journal_id.id,
                        "account_id": inv.partner_id.property_account_receivable.id,
                        "period_id": account_voucher_obj._get_period(),
                        "partner_id": self.env['res.partner']._find_accounting_partner(
                            inv.partner_id).id,
                        "type": inv.type in (
                            'out_invoice', 'out_refund') and 'receipt' or 'payment'
                    })
                    self.env["account.voucher.line"].create({
                        "name": "",
                        "payment_option": "without_writeoff",
                        "amount": amount,
                        "voucher_id": voucher.id,
                        "partner_id": inv.partner_id.id,
                        "account_id": inv.partner_id.property_account_receivable.id,
                        "type": "cr",
                        "move_line_id": inv.move_id.line_id[0].id,
                    })
                    if self.type_id.validate_automatically_voucher:
                        voucher.button_proforma_voucher()

        return res