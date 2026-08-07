import random
from uuid import uuid4
from datetime import datetime, timedelta, timezone
import numpy as np
from typing import List, Dict, Any, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

from app.models.schemas import (
    User, UserProfile, Account, Device, Transaction,
    Session, BiometricsData, GeoInfo, ThreatIntelEntry
)

logger = logging.getLogger(__name__)


class DigitalTwinGenerator:
    """Generates realistic synthetic banking data for the digital twin environment."""

    def __init__(self):
        self.cities = [
            {"city": "New York", "country": "US", "lat": 40.7128, "lon": -74.0060},
            {"city": "Los Angeles", "country": "US", "lat": 34.0522, "lon": -118.2437},
            {"city": "Chicago", "country": "US", "lat": 41.8781, "lon": -87.6298},
            {"city": "London", "country": "GB", "lat": 51.5074, "lon": -0.1278},
            {"city": "Tokyo", "country": "JP", "lat": 35.6762, "lon": 139.6503},
            {"city": "San Francisco", "country": "US", "lat": 37.7749, "lon": -122.4194},
            {"city": "Berlin", "country": "DE", "lat": 52.5200, "lon": 13.4050},
            {"city": "Mumbai", "country": "IN", "lat": 19.0760, "lon": 72.8777},
            {"city": "Sydney", "country": "AU", "lat": -33.8688, "lon": 151.2093},
            {"city": "Toronto", "country": "CA", "lat": 43.6532, "lon": -79.3832},
        ]

        self.first_names = [
            "Emma", "Noah", "Olivia", "Liam", "Ava", "William", "Sophia", "Mason",
            "Isabella", "James", "Mia", "Benjamin", "Charlotte", "Elijah", "Amelia",
            "Lucas", "Harper", "Alexander", "Evelyn", "Daniel"
        ]
        self.last_names = [
            "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
            "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Wilson", "Anderson",
            "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee"
        ]
        self.domains = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "protonmail.com"]
        self.os_options = ["Windows 11", "Windows 10", "macOS 14", "iOS 17", "Android 14", "Linux"]
        self.browser_options = ["Chrome 120", "Safari 17", "Firefox 121", "Edge 120"]
        self.merchant_names = [
            "Amazon", "Walmart", "Target", "BestBuy", "Starbucks", "Shell Gas",
            "Netflix", "Spotify", "UberEats", "DoorDash", "Apple Store", "Nike",
            "HomeDepot", "Costco", "Whole Foods", "CVS Pharmacy", "McDonalds",
            "Delta Airlines", "Hilton Hotels", "Steam Games"
        ]

        # Maps user_id -> [device objects] for proper association
        self._user_device_map: Dict[str, List[Device]] = {}

    def generate_users(self, n: int = 50) -> List[User]:
        """Generate realistic synthetic users."""
        users = []
        for _ in range(n):
            first = random.choice(self.first_names)
            last = random.choice(self.last_names)
            email = f"{first.lower()}.{last.lower()}{random.randint(1, 999)}@{random.choice(self.domains)}"
            phone = f"+1{random.randint(200, 999)}{random.randint(1000000, 9999999)}"
            city = random.choice(self.cities)

            profile = UserProfile(
                name=f"{first} {last}",
                email=email,
                phone=phone,
                address=f"{random.randint(100, 9999)} Main St, {city['city']}, {city['country']}"
            )

            risk_tier = np.random.choice(["low", "medium", "high"], p=[0.7, 0.2, 0.1])
            users.append(User(profile=profile, risk_tier=risk_tier))

        return users

    def generate_accounts(self, users: List[User], accounts_per_user: Tuple[int, int] = (1, 3)) -> List[Account]:
        """Generate bank/payment accounts for users."""
        accounts = []
        for user in users:
            num_accounts = random.randint(accounts_per_user[0], accounts_per_user[1])
            for _ in range(num_accounts):
                balance = round(random.uniform(500.0, 75000.0), 2)
                acct_type = np.random.choice(["checking", "savings", "credit"], p=[0.5, 0.3, 0.2])
                accounts.append(Account(user_id=user.user_id, balance=balance, account_type=acct_type))
        return accounts

    def generate_devices(self, users: List[User], devices_per_user: Tuple[int, int] = (1, 2)) -> List[Device]:
        """Generate synthetic devices and map them to users."""
        devices = []
        for user in users:
            num_devices = random.randint(devices_per_user[0], devices_per_user[1])
            user_devices = []
            for _ in range(num_devices):
                os_choice = random.choice(self.os_options)
                browser = random.choice(self.browser_options)
                device = Device(
                    fingerprint=uuid4().hex[:16],
                    os=os_choice,
                    browser=browser,
                    user_agent=f"{browser} on {os_choice}"
                )
                devices.append(device)
                user_devices.append(device)
            self._user_device_map[user.user_id] = user_devices
        return devices

    def generate_merchants(self, n: int = 30) -> List[Dict[str, Any]]:
        """Generate synthetic merchants."""
        categories = ["retail", "grocery", "entertainment", "travel", "digital_goods", "food", "gas", "pharmacy"]
        merchants = []
        for i in range(n):
            name = self.merchant_names[i % len(self.merchant_names)] if i < len(self.merchant_names) else f"Store-{random.randint(1000, 9999)}"
            merchants.append({
                "merchant_id": str(uuid4()),
                "name": name,
                "category": random.choice(categories),
                "risk_level": np.random.choice(["low", "medium", "high"], p=[0.8, 0.15, 0.05])
            })
        return merchants

    def _get_user_home_city(self, user: User) -> Dict:
        """Assign a consistent 'home' city to a user based on their user_id hash."""
        idx = hash(user.user_id) % len(self.cities)
        return self.cities[idx]

    def generate_session(self, user: User, device: Device) -> Session:
        """Generate a realistic normal user session with biometrics."""
        home = self._get_user_home_city(user)
        geo = GeoInfo(
            ip=f"{random.randint(10, 200)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 254)}",
            country=home["country"],
            city=home["city"],
            latitude=home["lat"] + random.uniform(-0.05, 0.05),
            longitude=home["lon"] + random.uniform(-0.05, 0.05)
        )

        biometrics = BiometricsData(
            typing_speed=random.uniform(180.0, 400.0),
            typing_rhythm_variance=random.uniform(0.02, 0.15),
            mouse_speed=random.uniform(300.0, 700.0),
            mouse_pattern_deviation=random.uniform(0.02, 0.12),
            session_duration=random.uniform(60.0, 900.0),
            session_duration_anomaly=random.uniform(-0.5, 0.5)
        )

        return Session(
            user_id=user.user_id,
            device_id=device.device_id,
            biometrics=biometrics,
            geo=geo
        )

    def generate_normal_transaction(
        self, user: User, account: Account, device: Device, merchants: List[Dict[str, Any]]
    ) -> Tuple[Transaction, Session]:
        """Generate a regular benign transaction with its session."""
        session = self.generate_session(user, device)
        merchant = random.choice(merchants)

        # Log-normal distribution for amounts
        amount = round(float(np.random.lognormal(mean=3.0, sigma=1.2)), 2)
        amount = max(1.0, min(amount, 5000.0))

        txn = Transaction(
            account_id=account.account_id,
            user_id=user.user_id,
            amount=amount,
            merchant_id=merchant["merchant_id"],
            merchant_name=merchant["name"],
            device_id=device.device_id,
            session_id=session.session_id,
            geo=session.geo,
            is_fraud=False
        )
        return txn, session

    def generate_threat_intel_watchlist(self, n: int = 20) -> List[ThreatIntelEntry]:
        """Generate threat intelligence entries for known bad entities."""
        entries = []
        for _ in range(n):
            entry_type = random.choice(["ip", "device", "merchant"])
            if entry_type == "ip":
                value = f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"
            else:
                value = str(uuid4())

            entries.append(ThreatIntelEntry(
                type=entry_type,
                value=value,
                risk_level=np.random.choice(["high", "critical"], p=[0.7, 0.3]),
                source="digital_twin_generator"
            ))
        return entries

    async def seed_database(self, db: AsyncIOMotorDatabase) -> None:
        """Generate all data and insert into MongoDB."""
        logger.info("Generating synthetic users...")
        users = self.generate_users(50)

        logger.info("Generating accounts, devices, merchants...")
        accounts = self.generate_accounts(users)
        devices = self.generate_devices(users)
        merchants = self.generate_merchants(30)
        watchlist = self.generate_threat_intel_watchlist(20)

        # Insert users
        for u in users:
            await db["users"].insert_one(u.model_dump(mode="json"))
        logger.info(f"Inserted {len(users)} users")

        # Insert accounts
        for a in accounts:
            await db["accounts"].insert_one(a.model_dump(mode="json"))
        logger.info(f"Inserted {len(accounts)} accounts")

        # Insert devices
        for d in devices:
            await db["devices"].insert_one(d.model_dump(mode="json"))
        logger.info(f"Inserted {len(devices)} devices")

        # Insert merchants
        for m in merchants:
            await db["merchants"].insert_one(m)
        logger.info(f"Inserted {len(merchants)} merchants")

        # Insert threat intel
        for w in watchlist:
            await db["threat_intel"].insert_one(w.model_dump(mode="json"))
        logger.info(f"Inserted {len(watchlist)} threat intel entries")

        # Generate transaction + session history
        logger.info("Generating transaction history...")
        txn_count = 0
        session_count = 0

        for _ in range(200):
            user = random.choice(users)
            user_accounts = [a for a in accounts if a.user_id == user.user_id]
            user_devices = self._user_device_map.get(user.user_id, [])

            if not user_accounts:
                continue

            account = random.choice(user_accounts)
            device = random.choice(user_devices) if user_devices else random.choice(devices)

            txn, session = self.generate_normal_transaction(user, account, device, merchants)

            # Backdate the transaction
            days_ago = random.randint(1, 30)
            hours_offset = random.randint(8, 22)  # Business-ish hours
            txn.timestamp = datetime.now(timezone.utc) - timedelta(days=days_ago, hours=hours_offset)
            session.started_at = txn.timestamp - timedelta(minutes=random.randint(1, 30))

            await db["sessions"].insert_one(session.model_dump(mode="json"))
            await db["transactions"].insert_one(txn.model_dump(mode="json"))
            txn_count += 1
            session_count += 1

        logger.info(f"Inserted {txn_count} transactions and {session_count} sessions")
        logger.info("Database seeding complete!")
