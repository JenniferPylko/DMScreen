import json
import os
import stripe
import logging
from dotenv import load_dotenv
from models import User, Users

from flask import Flask, jsonify, request

handler = logging.FileHandler('logs/stripe_webhook.log')
handler.setLevel(logging.DEBUG)
root_logger = logging.getLogger()
root_logger.addHandler(handler)
root_logger.setLevel(logging.DEBUG)
root_logger.debug('Starting webserver')
logging.basicConfig(level=logging.DEBUG, filename='stripe_webhook.log')

load_dotenv()

# This is your Stripe CLI webhook secret for testing your endpoint locally.

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    event = None
    payload = request.data
    sig_header = request.headers['STRIPE_SIGNATURE']

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv('STRIPE_WEBHOOK_SECRET')
        )
    except ValueError as e:
        # Invalid payload
        raise e
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        raise e

    # Handle the event
    logging.info("Intercepted event: " + event['type'])
    if event['type'] == 'account.updated':
      account = event['data']['object']
    elif event['type'] == 'account.external_account.created':
      external_account = event['data']['object']
    elif event['type'] == 'account.external_account.deleted':
      external_account = event['data']['object']
    elif event['type'] == 'account.external_account.updated':
      external_account = event['data']['object']
    elif event['type'] == 'balance.available':
      balance = event['data']['object']
    elif event['type'] == 'billing_portal.configuration.created':
      configuration = event['data']['object']
    elif event['type'] == 'billing_portal.configuration.updated':
      configuration = event['data']['object']
    elif event['type'] == 'billing_portal.session.created':
      session = event['data']['object']
    elif event['type'] == 'capability.updated':
      capability = event['data']['object']
    elif event['type'] == 'cash_balance.funds_available':
      cash_balance = event['data']['object']
    elif event['type'] == 'charge.captured':
      charge = event['data']['object']
    elif event['type'] == 'charge.expired':
      charge = event['data']['object']
    elif event['type'] == 'charge.failed':
      charge = event['data']['object']
    elif event['type'] == 'charge.pending':
      charge = event['data']['object']
    elif event['type'] == 'charge.refunded':
      charge = event['data']['object']
    elif event['type'] == 'charge.succeeded':
      charge = event['data']['object']
    elif event['type'] == 'charge.updated':
      charge = event['data']['object']
    elif event['type'] == 'charge.dispute.closed':
      dispute = event['data']['object']
    elif event['type'] == 'charge.dispute.created':
      dispute = event['data']['object']
    elif event['type'] == 'charge.dispute.funds_reinstated':
      dispute = event['data']['object']
    elif event['type'] == 'charge.dispute.funds_withdrawn':
      dispute = event['data']['object']
    elif event['type'] == 'charge.dispute.updated':
      dispute = event['data']['object']
    elif event['type'] == 'charge.refund.updated':
      refund = event['data']['object']
    elif event['type'] == 'checkout.session.async_payment_failed':
      session = event['data']['object']
    elif event['type'] == 'checkout.session.async_payment_succeeded':
      session = event['data']['object']
      user_id = session['client_reference_id']
      price_id = session['items']['plan']['id']
      logging.info('User {} paid for order: {}'.format(user_id, price_id))
      fulfill_order(user_id, price_id)
    elif event['type'] == 'checkout.session.completed':
      session = event['data']['object']
      user_id = session['client_reference_id']
      invoice_id = session['invoice']
      logging.info('User {} paid for order. (Invoice: {})'.format(user_id, invoice_id))
      User(user_id).update(stripe_invoice_id=invoice_id)
    elif event['type'] == 'checkout.session.expired':
      session = event['data']['object']
    elif event['type'] == 'coupon.created':
      coupon = event['data']['object']
    elif event['type'] == 'coupon.deleted':
      coupon = event['data']['object']
    elif event['type'] == 'coupon.updated':
      coupon = event['data']['object']
    elif event['type'] == 'credit_note.created':
      credit_note = event['data']['object']
    elif event['type'] == 'credit_note.updated':
      credit_note = event['data']['object']
    elif event['type'] == 'credit_note.voided':
      credit_note = event['data']['object']
    elif event['type'] == 'customer.created':
      customer = event['data']['object']
    elif event['type'] == 'customer.deleted':
      customer = event['data']['object']
    elif event['type'] == 'customer.updated':
      customer = event['data']['object']
    elif event['type'] == 'customer.discount.created':
      discount = event['data']['object']
    elif event['type'] == 'customer.discount.deleted':
      discount = event['data']['object']
    elif event['type'] == 'customer.discount.updated':
      discount = event['data']['object']
    elif event['type'] == 'customer.source.created':
      source = event['data']['object']
    elif event['type'] == 'customer.source.deleted':
      source = event['data']['object']
    elif event['type'] == 'customer.source.expiring':
      source = event['data']['object']
    elif event['type'] == 'customer.source.updated':
      source = event['data']['object']
    elif event['type'] == 'customer.subscription.created':
      subscription = event['data']['object']
    elif event['type'] == 'customer.subscription.deleted':
      subscription = event['data']['object']
    elif event['type'] == 'customer.subscription.paused':
      subscription = event['data']['object']
    elif event['type'] == 'customer.subscription.pending_update_applied':
      subscription = event['data']['object']
    elif event['type'] == 'customer.subscription.pending_update_expired':
      subscription = event['data']['object']
    elif event['type'] == 'customer.subscription.resumed':
      subscription = event['data']['object']
    elif event['type'] == 'customer.subscription.trial_will_end':
      subscription = event['data']['object']
    elif event['type'] == 'customer.subscription.updated':
      subscription = event['data']['object']
    elif event['type'] == 'customer.tax_id.created':
      tax_id = event['data']['object']
    elif event['type'] == 'customer.tax_id.deleted':
      tax_id = event['data']['object']
    elif event['type'] == 'customer.tax_id.updated':
      tax_id = event['data']['object']
    elif event['type'] == 'customer_cash_balance_transaction.created':
      customer_cash_balance_transaction = event['data']['object']
    elif event['type'] == 'file.created':
      file = event['data']['object']
    elif event['type'] == 'financial_connections.account.created':
      account = event['data']['object']
    elif event['type'] == 'financial_connections.account.deactivated':
      account = event['data']['object']
    elif event['type'] == 'financial_connections.account.disconnected':
      account = event['data']['object']
    elif event['type'] == 'financial_connections.account.reactivated':
      account = event['data']['object']
    elif event['type'] == 'financial_connections.account.refreshed_balance':
      account = event['data']['object']
    elif event['type'] == 'identity.verification_session.canceled':
      verification_session = event['data']['object']
    elif event['type'] == 'identity.verification_session.created':
      verification_session = event['data']['object']
    elif event['type'] == 'identity.verification_session.processing':
      verification_session = event['data']['object']
    elif event['type'] == 'identity.verification_session.requires_input':
      verification_session = event['data']['object']
    elif event['type'] == 'identity.verification_session.verified':
      verification_session = event['data']['object']
    elif event['type'] == 'invoice.created':
      invoice = event['data']['object']
    elif event['type'] == 'invoice.deleted':
      invoice = event['data']['object']
    elif event['type'] == 'invoice.finalization_failed':
      invoice = event['data']['object']
    elif event['type'] == 'invoice.finalized':
      invoice = event['data']['object']
    elif event['type'] == 'invoice.marked_uncollectible':
      invoice = event['data']['object']
    elif event['type'] == 'invoice.paid':
      invoice = event['data']['object']
    elif event['type'] == 'invoice.payment_action_required':
      invoice = event['data']['object']
    elif event['type'] == 'invoice.payment_failed':
      invoice = event['data']['object']
    elif event['type'] == 'invoice.payment_succeeded':
      invoice = event['data']['object']
      invoice_id = invoice['id']
      user = Users().get_by_stripe_invoice_id(invoice_id)
      if (user is not None):
        logging.debug('Received Payment for invoice_id: {}, ({})'.format(invoice_id, user.data['id']))
        user.update(membership='basic', stripe_customer_id=invoice['customer'])
    elif event['type'] == 'invoice.sent':
      invoice = event['data']['object']
    elif event['type'] == 'invoice.upcoming':
      invoice = event['data']['object']
    elif event['type'] == 'invoice.updated':
      invoice = event['data']['object']
    elif event['type'] == 'invoice.voided':
      invoice = event['data']['object']
    elif event['type'] == 'invoiceitem.created':
      invoiceitem = event['data']['object']
    elif event['type'] == 'invoiceitem.deleted':
      invoiceitem = event['data']['object']
    elif event['type'] == 'invoiceitem.updated':
      invoiceitem = event['data']['object']
    elif event['type'] == 'issuing_authorization.created':
      issuing_authorization = event['data']['object']
    elif event['type'] == 'issuing_authorization.updated':
      issuing_authorization = event['data']['object']
    elif event['type'] == 'issuing_card.created':
      issuing_card = event['data']['object']
    elif event['type'] == 'issuing_card.updated':
      issuing_card = event['data']['object']
    elif event['type'] == 'issuing_cardholder.created':
      issuing_cardholder = event['data']['object']
    elif event['type'] == 'issuing_cardholder.updated':
      issuing_cardholder = event['data']['object']
    elif event['type'] == 'issuing_dispute.closed':
      issuing_dispute = event['data']['object']
    elif event['type'] == 'issuing_dispute.created':
      issuing_dispute = event['data']['object']
    elif event['type'] == 'issuing_dispute.funds_reinstated':
      issuing_dispute = event['data']['object']
    elif event['type'] == 'issuing_dispute.submitted':
      issuing_dispute = event['data']['object']
    elif event['type'] == 'issuing_dispute.updated':
      issuing_dispute = event['data']['object']
    elif event['type'] == 'issuing_transaction.created':
      issuing_transaction = event['data']['object']
    elif event['type'] == 'issuing_transaction.updated':
      issuing_transaction = event['data']['object']
    elif event['type'] == 'mandate.updated':
      mandate = event['data']['object']
    elif event['type'] == 'order.created':
      order = event['data']['object']
    elif event['type'] == 'payment_intent.amount_capturable_updated':
      payment_intent = event['data']['object']
    elif event['type'] == 'payment_intent.canceled':
      payment_intent = event['data']['object']
    elif event['type'] == 'payment_intent.created':
      payment_intent = event['data']['object']
    elif event['type'] == 'payment_intent.partially_funded':
      payment_intent = event['data']['object']
    elif event['type'] == 'payment_intent.payment_failed':
      payment_intent = event['data']['object']
    elif event['type'] == 'payment_intent.processing':
      payment_intent = event['data']['object']
    elif event['type'] == 'payment_intent.requires_action':
      payment_intent = event['data']['object']
    elif event['type'] == 'payment_intent.succeeded':
      payment_intent = event['data']['object']
    elif event['type'] == 'payment_link.created':
      payment_link = event['data']['object']
    elif event['type'] == 'payment_link.updated':
      payment_link = event['data']['object']
    elif event['type'] == 'payment_method.attached':
      payment_method = event['data']['object']
    elif event['type'] == 'payment_method.automatically_updated':
      payment_method = event['data']['object']
    elif event['type'] == 'payment_method.detached':
      payment_method = event['data']['object']
    elif event['type'] == 'payment_method.updated':
      payment_method = event['data']['object']
    elif event['type'] == 'payout.canceled':
      payout = event['data']['object']
    elif event['type'] == 'payout.created':
      payout = event['data']['object']
    elif event['type'] == 'payout.failed':
      payout = event['data']['object']
    elif event['type'] == 'payout.paid':
      payout = event['data']['object']
    elif event['type'] == 'payout.reconciliation_completed':
      payout = event['data']['object']
    elif event['type'] == 'payout.updated':
      payout = event['data']['object']
    elif event['type'] == 'person.created':
      person = event['data']['object']
    elif event['type'] == 'person.deleted':
      person = event['data']['object']
    elif event['type'] == 'person.updated':
      person = event['data']['object']
    elif event['type'] == 'plan.created':
      plan = event['data']['object']
    elif event['type'] == 'plan.deleted':
      plan = event['data']['object']
    elif event['type'] == 'plan.updated':
      plan = event['data']['object']
    elif event['type'] == 'price.created':
      price = event['data']['object']
    elif event['type'] == 'price.deleted':
      price = event['data']['object']
    elif event['type'] == 'price.updated':
      price = event['data']['object']
    elif event['type'] == 'product.created':
      product = event['data']['object']
    elif event['type'] == 'product.deleted':
      product = event['data']['object']
    elif event['type'] == 'product.updated':
      product = event['data']['object']
    elif event['type'] == 'promotion_code.created':
      promotion_code = event['data']['object']
    elif event['type'] == 'promotion_code.updated':
      promotion_code = event['data']['object']
    elif event['type'] == 'quote.accepted':
      quote = event['data']['object']
    elif event['type'] == 'quote.canceled':
      quote = event['data']['object']
    elif event['type'] == 'quote.created':
      quote = event['data']['object']
    elif event['type'] == 'quote.finalized':
      quote = event['data']['object']
    elif event['type'] == 'radar.early_fraud_warning.created':
      early_fraud_warning = event['data']['object']
    elif event['type'] == 'radar.early_fraud_warning.updated':
      early_fraud_warning = event['data']['object']
    elif event['type'] == 'recipient.created':
      recipient = event['data']['object']
    elif event['type'] == 'recipient.deleted':
      recipient = event['data']['object']
    elif event['type'] == 'recipient.updated':
      recipient = event['data']['object']
    elif event['type'] == 'refund.created':
      refund = event['data']['object']
    elif event['type'] == 'refund.updated':
      refund = event['data']['object']
    elif event['type'] == 'reporting.report_run.failed':
      report_run = event['data']['object']
    elif event['type'] == 'reporting.report_run.succeeded':
      report_run = event['data']['object']
    elif event['type'] == 'review.closed':
      review = event['data']['object']
    elif event['type'] == 'review.opened':
      review = event['data']['object']
    elif event['type'] == 'setup_intent.canceled':
      setup_intent = event['data']['object']
    elif event['type'] == 'setup_intent.created':
      setup_intent = event['data']['object']
    elif event['type'] == 'setup_intent.requires_action':
      setup_intent = event['data']['object']
    elif event['type'] == 'setup_intent.setup_failed':
      setup_intent = event['data']['object']
    elif event['type'] == 'setup_intent.succeeded':
      setup_intent = event['data']['object']
    elif event['type'] == 'sigma.scheduled_query_run.created':
      scheduled_query_run = event['data']['object']
    elif event['type'] == 'sku.created':
      sku = event['data']['object']
    elif event['type'] == 'sku.deleted':
      sku = event['data']['object']
    elif event['type'] == 'sku.updated':
      sku = event['data']['object']
    elif event['type'] == 'source.canceled':
      source = event['data']['object']
    elif event['type'] == 'source.chargeable':
      source = event['data']['object']
    elif event['type'] == 'source.failed':
      source = event['data']['object']
    elif event['type'] == 'source.mandate_notification':
      source = event['data']['object']
    elif event['type'] == 'source.refund_attributes_required':
      source = event['data']['object']
    elif event['type'] == 'source.transaction.created':
      transaction = event['data']['object']
    elif event['type'] == 'source.transaction.updated':
      transaction = event['data']['object']
    elif event['type'] == 'subscription_schedule.aborted':
      subscription_schedule = event['data']['object']
    elif event['type'] == 'subscription_schedule.canceled':
      subscription_schedule = event['data']['object']
    elif event['type'] == 'subscription_schedule.completed':
      subscription_schedule = event['data']['object']
    elif event['type'] == 'subscription_schedule.created':
      subscription_schedule = event['data']['object']
    elif event['type'] == 'subscription_schedule.expiring':
      subscription_schedule = event['data']['object']
    elif event['type'] == 'subscription_schedule.released':
      subscription_schedule = event['data']['object']
    elif event['type'] == 'subscription_schedule.updated':
      subscription_schedule = event['data']['object']
    elif event['type'] == 'tax.settings.updated':
      settings = event['data']['object']
    elif event['type'] == 'tax_rate.created':
      tax_rate = event['data']['object']
    elif event['type'] == 'tax_rate.updated':
      tax_rate = event['data']['object']
    elif event['type'] == 'terminal.reader.action_failed':
      reader = event['data']['object']
    elif event['type'] == 'terminal.reader.action_succeeded':
      reader = event['data']['object']
    elif event['type'] == 'test_helpers.test_clock.advancing':
      test_clock = event['data']['object']
    elif event['type'] == 'test_helpers.test_clock.created':
      test_clock = event['data']['object']
    elif event['type'] == 'test_helpers.test_clock.deleted':
      test_clock = event['data']['object']
    elif event['type'] == 'test_helpers.test_clock.internal_failure':
      test_clock = event['data']['object']
    elif event['type'] == 'test_helpers.test_clock.ready':
      test_clock = event['data']['object']
    elif event['type'] == 'topup.canceled':
      topup = event['data']['object']
    elif event['type'] == 'topup.created':
      topup = event['data']['object']
    elif event['type'] == 'topup.failed':
      topup = event['data']['object']
    elif event['type'] == 'topup.reversed':
      topup = event['data']['object']
    elif event['type'] == 'topup.succeeded':
      topup = event['data']['object']
    elif event['type'] == 'transfer.created':
      transfer = event['data']['object']
    elif event['type'] == 'transfer.reversed':
      transfer = event['data']['object']
    elif event['type'] == 'transfer.updated':
      transfer = event['data']['object']
    else:
      logging.warn('Unhandled event type {}'.format(event['type']))

    return jsonify(success=True)

    return Response(status=200)

def fulfill_order(userid, line_items):
    # TODO:
    logging.debug('Fulfilling Order')
    user = User(userid)
    user.update(membership='basic')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4242)
