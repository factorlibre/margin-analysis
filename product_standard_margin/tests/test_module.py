# Copyright (C) 2020 - Today: GRAP (http://www.grap.coop)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import TransactionCase


class TestModule(TransactionCase):

    def setUp(self):
        super().setUp()
        self.ProductProduct = self.env['product.product']
        self.ProductTemplate = self.env['product.template']
        self.product_template = self.ProductTemplate.create({
            'name': 'Demo template',
            'lst_price': 100,
        })
        self.product_product = self.ProductProduct.create({
            'name': 'Demo template',
            'product_tmpl_id': self.product_template.id,
            'lst_price': 100,
        })

    # Custom Section
    def _create_product(self, model, standard_price, sale_price, sale_tax_ids):
        if model == 'product':
            ModelObj = self.ProductProduct
        else:
            ModelObj = self.ProductTemplate
        return ModelObj.create({
            'name': 'Demo Product',
            'standard_price': standard_price,
            'lst_price': sale_price,
            'taxes_id': [(6, 0, sale_tax_ids)],
        })

    # Test Section
    def test_01_classic_margin(self):
        for model in ['product', 'template']:
            product = self._create_product(model, 50, 200, [])
            self.assertEqual(
                product.standard_margin, 150,
                "Incorrect Standard Margin for model %s" % model)
            self.assertEqual(
                product.standard_margin_rate, 75.0,
                "Incorrect Standard Margin Rate for model %s" % model)

    def test_02_margin_without_standard_price(self):
        for model in ['product', 'template']:
            product = self._create_product(model, 0, 200, [])
            self.assertEqual(
                product.standard_margin, 200,
                "Incorrect Standard Margin (without standard price)"
                " for model %s" % model)
            self.assertEqual(
                product.standard_margin_rate, 100.0,
                "Incorrect Standard Margin Rate (without standard price)"
                " for model %s" % model)

    def test_03_margin_without_sale_price(self):
        for model in ['product', 'template']:
            product = self._create_product(model, 50, 0, [])
            self.assertEqual(
                product.standard_margin, -50,
                "Incorrect Standard Margin (without sale price)"
                " for model %s" % model)
            self.assertEqual(
                product.standard_margin_rate, 999.0,
                "Incorrect Standard Margin Rate (without sale price)"
                " for model %s" % model)

    def test_04_include_tax_include(self):
        tax = self.env["account.tax"].create(
            {
                "name": "impuesto 10 incluido",
                "amount": 10,
                "price_include": True,
                "include_base_amount": True,
            }
        )
        self.env['ir.config_parameter'].sudo().set_param(
                'product_standard_margin.margin_tax', 'include')
        self.product_template.write({
            'taxes_id': [(6, 0, tax.ids)]
        })
        self.product_template.standard_price = 10
        self.assertEqual(
            self.product_template.standard_margin, 80.91)
        self.product_product.write({
            'taxes_id': [(6, 0, tax.ids)]
        })
        self.product_product.standard_price = 10
        self.assertEqual(
            self.product_product.standard_margin, 80.91)

    def test_05_include_tax_exclude(self):
        tax = self.env['account.tax'].create(
            {'name': 'impuesto 10 excluido', 'amount': 10})
        self.env['ir.config_parameter'].sudo().set_param(
                'product_standard_margin.margin_tax', 'include')
        self.product_template.write({
            'taxes_id': [(6, 0, tax.ids)]
        })
        self.product_template.standard_price = 10
        self.assertEqual(
            self.product_template.standard_margin, 80.91)
        self.product_product.write({
            'taxes_id': [(6, 0, tax.ids)]
        })
        self.product_product.standard_price = 10
        self.assertEqual(
            self.product_product.standard_margin, 80.91)

    def test_06_exclude_tax_exclude(self):
        tax = self.env['account.tax'].create(
            {'name': 'impuesto 10 excluido', 'amount': 10})
        self.env['ir.config_parameter'].sudo().set_param(
                'product_standard_margin.margin_tax', 'exclude')
        self.product_template.write({
            'taxes_id': [(6, 0, tax.ids)]
        })
        self.product_template.write({
            'standard_price': 10
        })
        self.product_template.standard_price = 10
        self.assertEqual(
            self.product_template.standard_margin, 90)
        self.product_product.write({
            'taxes_id': [(6, 0, tax.ids)]
        })
        self.product_product.standard_price = 10
        self.assertEqual(
            self.product_product.standard_price, 10)
        self.assertEqual(
            self.product_product.standard_margin, 90)

    def test_07_exclude_tax_include(self):
        tax = self.env["account.tax"].create(
            {
                "name": "impuesto 10 incluido",
                "amount": 10,
                "price_include": True,
                "include_base_amount": True,
            }
        )
        self.env['ir.config_parameter'].sudo().set_param(
                'product_standard_margin.margin_tax', 'exclude')
        self.product_template.write({
            'taxes_id': [(6, 0, tax.ids)]
        })
        self.product_template.write({
            'standard_price': 10
        })
        self.product_template.standard_price = 10
        self.assertEqual(
            self.product_template.standard_margin, 90)
        self.product_product.write({
            'taxes_id': [(6, 0, tax.ids)]
        })
        self.product_product.standard_price = 10
        self.assertEqual(
            self.product_product.standard_price, 10)
        self.assertEqual(
            self.product_product.standard_margin, 90)
