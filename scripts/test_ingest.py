#!/usr/bin/env python3
"""
Test script for AiSMS ingest endpoint
Sends sample events to verify the backend is working correctly
"""

import requests
import json
import time
from datetime import datetime, timezone
import random

# Configuration
API_BASE = "http://localhost:8001"
API_KEY = "dev-ingest-key"  # Change to your actual key
DEVICE_ID = "test_device_1"

# Emotion labels
EMOTIONS = ["Happy", "Sad", "Angry", "Surprise", "Fear", "Disgust", "Neutral"]

def generate_random_event(student_id):
    """Generate a random event for testing"""
    
    # Random emotion
    emotion = random.choice(EMOTIONS)
    
    # Generate probabilities (sum to 1)
    probs = {e: random.random() for e in EMOTIONS}
    total = sum(probs.values())
    probs = {e: v/total for e, v in probs.items()}
    
    # Metrics
    engagement = random.uniform(0.3, 0.95)
    boredom = random.uniform(0.0, 0.4)
    frustration = random.uniform(0.0, 0.3)
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "student_id": student_id,
        "face_match_confidence": random.uniform(0.7, 0.99),
        "emotion": emotion,
        "emotion_confidence": probs[emotion],
        "probabilities": probs,
        "metrics": {
            "engagement": engagement,
            "boredom": boredom,
            "frustration": frustration,
            "attentiveness": random.uniform(0.4, 0.95),
            "positivity": random.uniform(0.3, 0.9),
            "volatility": random.uniform(0.0, 0.5),
            "distraction": random.uniform(0.0, 0.4),
            "fatigue": random.uniform(0.0, 0.3),
            "risk": random.uniform(0.0, 0.5)
        },
        "ear": random.uniform(0.15, 0.35),
        "head_pose": {
            "yaw": random.uniform(-30, 30),
            "pitch": random.uniform(-20, 20),
            "roll": random.uniform(-15, 15)
        },
        "source_device": DEVICE_ID
    }

def test_single_event():
    """Test sending a single event"""
    print("\n📤 Testing single event ingestion...")
    
    event = generate_random_event("TEST_STUDENT_001")
    
    response = requests.post(
        f"{API_BASE}/ingest",
        headers={
            "X-API-KEY": API_KEY,
            "Content-Type": "application/json"
        },
        json=event
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Single event ingested successfully: {result}")
        return True
    else:
        print(f"❌ Failed to ingest event: {response.status_code}")
        print(f"   Response: {response.text}")
        return False

def test_batch_events(count=5):
    """Test sending multiple events in batch"""
    print(f"\n📤 Testing batch ingestion ({count} events)...")
    
    events = []
    student_ids = [f"TEST_STUDENT_{str(i).zfill(3)}" for i in range(1, 4)]
    
    for _ in range(count):
        student_id = random.choice(student_ids)
        events.append(generate_random_event(student_id))
    
    response = requests.post(
        f"{API_BASE}/ingest",
        headers={
            "X-API-KEY": API_KEY,
            "Content-Type": "application/json"
        },
        json={"events": events}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Batch events ingested successfully: {result}")
        return True
    else:
        print(f"❌ Failed to ingest batch: {response.status_code}")
        print(f"   Response: {response.text}")
        return False

def test_invalid_api_key():
    """Test with invalid API key"""
    print("\n🔒 Testing invalid API key...")
    
    event = generate_random_event("TEST_STUDENT_001")
    
    response = requests.post(
        f"{API_BASE}/ingest",
        headers={
            "X-API-KEY": "wrong-key",
            "Content-Type": "application/json"
        },
        json=event
    )
    
    if response.status_code == 401:
        print("✅ Correctly rejected invalid API key")
        return True
    else:
        print(f"❌ Unexpected response: {response.status_code}")
        return False

def test_continuous_stream(duration_seconds=30, rate_per_second=2):
    """Test continuous event stream"""
    print(f"\n🌊 Testing continuous stream for {duration_seconds} seconds...")
    print(f"   Rate: {rate_per_second} events/second")
    
    student_ids = [f"TEST_STUDENT_{str(i).zfill(3)}" for i in range(1, 6)]
    start_time = time.time()
    count = 0
    
    try:
        while time.time() - start_time < duration_seconds:
            student_id = random.choice(student_ids)
            event = generate_random_event(student_id)
            
            response = requests.post(
                f"{API_BASE}/ingest",
                headers={
                    "X-API-KEY": API_KEY,
                    "Content-Type": "application/json"
                },
                json=event
            )
            
            if response.status_code == 200:
                count += 1
                print(f"✓ Sent {count} events", end='\r')
            else:
                print(f"\n❌ Failed at event {count}: {response.status_code}")
            
            time.sleep(1.0 / rate_per_second)
        
        print(f"\n✅ Continuous stream test completed: {count} events sent")
        return True
    
    except KeyboardInterrupt:
        print(f"\n⚠️  Stream interrupted by user after {count} events")
        return True
    except Exception as e:
        print(f"\n❌ Stream failed: {e}")
        return False

def check_health():
    """Check if backend is healthy"""
    print("🏥 Checking backend health...")
    
    try:
        response = requests.get(f"{API_BASE}/health")
        if response.status_code == 200:
            health = response.json()
            print(f"✅ Backend is healthy: {health}")
            return True
        else:
            print(f"❌ Backend health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to backend: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 50)
    print("AiSMS Ingest API Test Suite")
    print("=" * 50)
    
    # Check health first
    if not check_health():
        print("\n❌ Backend is not accessible. Please start the backend first.")
        return
    
    # Run tests
    results = []
    
    results.append(("Single Event", test_single_event()))
    time.sleep(1)
    
    results.append(("Batch Events", test_batch_events(5)))
    time.sleep(1)
    
    results.append(("Invalid API Key", test_invalid_api_key()))
    time.sleep(1)
    
    # Ask if user wants continuous stream test
    print("\n" + "=" * 50)
    response = input("Run continuous stream test? (y/n): ")
    if response.lower() == 'y':
        results.append(("Continuous Stream", test_continuous_stream(30, 2)))
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary:")
    print("=" * 50)
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:.<30} {status}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your ingest API is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")

if __name__ == "__main__":
    main()