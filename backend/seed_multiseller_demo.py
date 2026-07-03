from backend import create_app
from backend.services.demo_seed import seed_multiseller_demo_data


def main():
    app = create_app()
    with app.app_context():
        summary = seed_multiseller_demo_data()

    print('Multi-seller demo data seeded successfully.')
    print(f"Buyer username: {summary['buyer_username']} / {summary['buyer_password']}")
    print(f"Buyer userid: {summary['buyer_id']}")
    print(f"Seller password: {summary['seller_password']}")
    for seller in summary['seller_accounts']:
        print(f"Seller username: {seller['username']} / {summary['seller_password']}")
        print(f"Seller userid: {seller['userid']}")
    print(f"Products: {summary['product_count']}")
    print(f"Orders: {summary['order_count']}")


if __name__ == '__main__':
    main()
