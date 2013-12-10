# -*- coding: utf-8 -*-
##############################################################################
#
#    Author: Alexandre Fayolle
#    Copyright 2012 Camptocamp SA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv.orm import Model
from openerp.osv import fields
import decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)

class Product(Model):
    _inherit = 'product.product'

    def _compute_purchase_price(self, cr, uid, ids,
                                context=None):
        '''
        Compute the purchase price, taking into account sub products and routing
        '''
        if context is None:
            context = {}
        product_uom = context.get('product_uom')
        bom_properties = context.get('properties', [])

        bom_obj = self.pool.get('mrp.bom')
        uom_obj = self.pool.get('product.uom')

        res = {}
        ids = ids or []

        product_without_bom_ids = []
        for pr in self.read(cr, uid, ids, ['id','name'], context=context):
            bom_id = bom_obj._bom_find(cr, uid, pr['id'], product_uom=product_uom, 
                                       properties=bom_properties)
            if not bom_id: # no BoM: use standard_price
                product_without_bom_ids.append(pr['id'])
                continue
            _logger.debug("look for product named %s, bom_id is %s",
            pr['name'], bom_id)
            bom = bom_obj.browse(cr, uid, bom_id)
            sub_products, routes = bom_obj._bom_explode(cr, uid, bom,
                                                        factor=1,
                                                        properties=bom_properties,
                                                        # addthis=False)
                                                        addthis=True)
            _logger.debug("bom_explode_result: %s", sub_products)
            price = 0.
            for sub_product_dict in sub_products:
                sub_product = self.read(cr, uid, 
                                          sub_product_dict['product_id'],
                                          ['cost_price','uom_po_id','name'],
                                          context=context)
                std_price = sub_product['cost_price']
                qty = uom_obj._compute_qty(cr, uid,
                                           from_uom_id = sub_product_dict['product_uom'],
                                           qty         = sub_product_dict['product_qty'],
                                           to_uom_id   = sub_product['uom_po_id'][0])
                price += std_price * qty
                _logger.debug("price (%s) * qty (%s) for subproduct %s is %s",
                              std_price, qty, sub_product['name'], std_price * qty)
            if bom.routing_id:
                for wline in bom.routing_id.workcenter_lines:
                    wc = wline.workcenter_id
                    cycle = wline.cycle_nbr
                    hour = ((wc.time_start + wc.time_stop + cycle * wc.time_cycle) 
                            * (wc.time_efficiency or 1.0))
                    price += wc.costs_cycle * cycle + wc.costs_hour * hour
                _logger.debug("the bom has a routing id %s, price is now %s",
                              bom.routing_id, price)
            price /= bom.product_qty
            price = uom_obj._compute_price(cr, uid, bom.product_uom.id,
                price, bom.product_id.uom_id.id)
            res[pr['id']] = price
            _logger.debug("total price is %s for %s (id:%s)",
                              price, pr['name'], pr['id'])
        if product_without_bom_ids:
            standard_prices = super(Product, self)._compute_purchase_price(
                cr, uid, product_without_bom_ids, context=context)
            res.update(standard_prices)
        return res


    def _cost_price(self, cr, uid, ids, field_name, arg, context=None):
        if context is None:
            context = {}
        res = self._compute_purchase_price(cr, uid, ids, context=context)
        _logger.debug("get cost field _cost_price %s, arg: %s, context: %s, result:%s",
            field_name, arg, context, res)
        return res

    def _get_bom_product(self, cr, uid, ids, context=None):
        """return ids of modified product and ids of all product that use
        as sub-product one of this ids. Ex:
        BoM : 
            Product A
                -   Product B
                -   Product C
        => If we change standard_price of product B, we want to update Product 
        A as well...
        @param: ids of products
        """
        def _get_parent_bom(bom_record):
            """
            Recursvely find the parent bom of all impacted products
            and return list of bom ids
            """
            bom_result=[]
            bom_obj = self.pool.get('mrp.bom')
            if bom_record.bom_id:
                bom_result.append(bom_record.bom_id.id)
                bom_result.extend(_get_parent_bom(bom_record.bom_id))
            return bom_result
         
         # def _get_product_bom_existing(product_record):
         #    """
         #    faire pareil mais regarder pour les produits si a une autre parent bom si 
         #    pas sortir de la boucle. appeler _get_parent_bom pour savoir ça
         #    """
         #    product_result=[]
         #    bom_obj = self.pool.get('mrp.bom')
         #    bom_ids = bom_obj.search(cr, uid, [('product_id','=',product.id)], 
         #                        context=context)
         #    for bom in bom_obj.browse(cr, uid, bom_ids, context=context):
         #        res = _get_parent_bom(bom)
         #    return True

        res = []
        product_ids = ids
        bom_obj = self.pool.get('mrp.bom')
        bom_ids = bom_obj.search(cr, uid, [('product_id','in',ids)], 
                                context=context)
        if bom_ids:
            final_bom_ids=bom_ids
            for bom in bom_obj.browse(cr, uid, bom_ids, context=context):
                res = _get_parent_bom(bom)
            final_bom_ids = list(set(res + bom_ids))
            product_ids = list(set(ids + self._get_product_id_from_bom(cr, uid, final_bom_ids,
                                                    context=context)))
            
            # result = self._get_bom_product(cr, uid, product_ids, context=context)
            # product_ids.extend(result)
            # #manque condition de sortie
        _logger.debug("trigger on product.product model for product ids %s",product_ids)
        return product_ids
        
    def _get_product(self, cr, uid, ids, context=None):
        """
        Return all product impacted from a change in a bom, that means
        current product and all parent that is composed by it.
        """
        context = context or {}
        bom_obj = self.pool.get('mrp.bom')
        prod_obj = self.pool.get('product.product')
        res = {}
        for bom in bom_obj.read(cr, uid, ids, ['product_id'],context=context):
        # for bom in bom_obj.browse(cr, uid, ids, context=context):
            res[bom['product_id'][0]] = True
        final_res = prod_obj._get_bom_product(cr, uid, res.keys(), context=context)
        _logger.debug("trigger on mrp.bom model for product ids %s",final_res)
        return final_res
    
    def _get_product_id_from_bom(self, cr, uid, ids, context=None):
        """
        Return a list of product ids from bom
        """
        context = context or {}
        bom_obj = self.pool.get('mrp.bom')
        res = {}
        for bom in bom_obj.read(cr, uid, ids, ['product_id'], context=context):
        # for bom in bom_obj.browse(cr, uid, ids, context=context):
            res[bom['product_id'][0]] = True
        return res.keys()

    def _get_poduct_from_template2(self, cr, uid, ids, context=None):
        prod_obj = self.pool.get('product.product')
        return prod_obj._get_poduct_from_template(cr, uid, ids, context=context)

   # Trigger on product.product is set to None, otherwise do not trigg
    # on product creation !
    _cost_price_triggers = {
        'product.product': (_get_bom_product, None, 10),
        # 'product.product': (_get_bom_product, ['standard_price','bom_ids'], 20),
        'product.template': (_get_poduct_from_template2, ['standard_price'], 10),
        'mrp.bom': (_get_product, 
                   [
                     'bom_id',
                     'bom_lines',
                     'product_id',
                     'product_uom',
                     'product_qty',
                     'product_uos',
                     'product_uos_qty',
                   ],
                   10)
    }

    _columns = {
        'cost_price': fields.function(_cost_price,
              store=_cost_price_triggers,
              string='Cost Price (incl. BoM)',
              digits_compute=dp.get_precision('Sale Price'),
              help="The cost price is the standard price or, if the product has a bom, "
              "the sum of all standard price of its components. it take also care of the "
              "bom costing like cost per cylce.")
        }

