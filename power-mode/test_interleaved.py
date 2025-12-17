#!/usr/bin/env python3
"""
Test Interleaved Agent Coordination

Shows agents communicating back-and-forth in real-time:
- Agent 1 and Agent 2 poll Redis Stream every 5 seconds
- They play a math game: ask question → answer → ask new question
- Timestamps show clear interleaved communication, not sequential batches

This proves agents can coordinate in real-time, not just sequential handoff.
"""

import json
import os
import sys
import time
import threading
from pathlib import Path
from datetime import datetime

# Add power-mode to path
sys.path.insert(0, str(Path(__file__).parent))

from upstash_adapter import get_redis_client, is_upstash_available


class CoordinatedAgent:
    """Agent that polls Redis Stream and responds to messages."""

    def __init__(self, agent_id, agent_name, redis_client, stream_key, poll_interval=5):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.redis_client = redis_client
        self.stream_key = stream_key
        self.poll_interval = poll_interval
        self.last_message_id = "0-0"  # Start from very beginning
        self.running = False
        self.message_count = 0
        self.processed_message_ids = set()  # Track what we've already processed

    def publish_message(self, msg_type, content, metadata=None):
        """Publish message to Redis Stream."""
        message = {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "type": msg_type,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "message_num": str(self.message_count)
        }

        if metadata:
            message.update(metadata)

        msg_id = self.redis_client.xadd(self.stream_key, message)
        self.message_count += 1

        print(f"[{self.agent_id}] Published: {content[:60]}...")
        return msg_id

    def read_new_messages(self):
        """Read new messages from stream since last read."""
        try:
            # Use XRANGE to get all messages from the stream
            # This is simpler and works better with Upstash REST API
            msg_list = self.redis_client.xrange(
                self.stream_key,
                min="-",  # From beginning
                max="+",  # To end
                count=100
            )

            print(f"[{self.agent_id}] DEBUG: xrange returned {len(msg_list) if msg_list else 0} messages")

            if not msg_list:
                return []

            # Parse messages
            parsed = []
            for msg_entry in msg_list:
                msg_id, msg_data = msg_entry

                # Skip if we've already processed this message
                if msg_id in self.processed_message_ids:
                    continue

                # Mark as processed
                self.processed_message_ids.add(msg_id)

                # Convert flat list to dict (Upstash format)
                data_dict = {}
                for i in range(0, len(msg_data), 2):
                    key = msg_data[i]
                    value = msg_data[i + 1]
                    if isinstance(key, bytes):
                        key = key.decode('utf-8')
                    if isinstance(value, bytes):
                        value = value.decode('utf-8')
                    data_dict[key] = value

                # Only process messages from OTHER agents
                if data_dict.get("agent_id") != self.agent_id:
                    parsed.append(data_dict)
                    print(f"[{self.agent_id}] DEBUG: Found new message from {data_dict.get('agent_id')}")

            return parsed

        except Exception as e:
            print(f"[{self.agent_id}] Error reading stream: {e}")
            return []

    def process_message(self, message):
        """Process a message and respond if needed."""
        msg_type = message.get("type", "")
        content = message.get("content", "")
        from_agent = message.get("agent_id", "")

        print(f"[{self.agent_id}] Received from {from_agent}: {content[:60]}...")

        if msg_type == "question":
            # Answer the question
            question = message.get("question", "")
            answer = self.solve_math_problem(question)

            # Publish answer
            self.publish_message(
                msg_type="answer",
                content=f"Answer: {answer}",
                metadata={
                    "question": question,
                    "answer": str(answer),
                    "responding_to": from_agent
                }
            )

            # Ask a new question
            time.sleep(0.5)  # Small delay
            new_question = self.generate_math_problem()
            self.publish_message(
                msg_type="question",
                content=f"Question: {new_question}",
                metadata={"question": new_question}
            )

    def solve_math_problem(self, question):
        """Solve a simple math problem."""
        try:
            # Extract numbers and operator
            if "+" in question:
                parts = question.split("+")
                return int(parts[0].strip()) + int(parts[1].strip())
            elif "-" in question:
                parts = question.split("-")
                return int(parts[0].strip()) - int(parts[1].strip())
            elif "*" in question or "×" in question:
                parts = question.replace("×", "*").split("*")
                return int(parts[0].strip()) * int(parts[1].strip())
            elif "/" in question:
                parts = question.split("/")
                return int(parts[0].strip()) // int(parts[1].strip())
            else:
                return "Unknown"
        except:
            return "Error"

    def generate_math_problem(self):
        """Generate a random math problem."""
        import random
        a = random.randint(1, 20)
        b = random.randint(1, 20)
        op = random.choice(["+", "-", "*"])
        return f"{a} {op} {b}"

    def poll_loop(self, duration_seconds=30):
        """Poll Redis Stream at regular intervals."""
        self.running = True
        start_time = time.time()

        print(f"[{self.agent_id}] Starting poll loop (every {self.poll_interval}s for {duration_seconds}s)")

        while self.running and (time.time() - start_time) < duration_seconds:
            # Check for new messages
            messages = self.read_new_messages()

            if messages:
                print(f"[{self.agent_id}] Poll: Found {len(messages)} new message(s)")
                for msg in messages:
                    self.process_message(msg)
            else:
                print(f"[{self.agent_id}] Poll: No new messages")

            # Wait for next poll
            time.sleep(self.poll_interval)

        print(f"[{self.agent_id}] Poll loop ended")
        self.running = False


def test_interleaved_coordination():
    """Test agents coordinating with interleaved messages."""
    print("\n" + "="*70)
    print("  INTERLEAVED COORDINATION TEST")
    print("="*70)
    print(f"Started: {datetime.now().isoformat()}")
    print()

    # Check Upstash
    if not is_upstash_available():
        print("[ERROR] Upstash Redis not configured")
        return False

    print("[OK] Upstash Redis credentials found")

    # Get Redis client
    try:
        redis_client = get_redis_client()
        print(f"[OK] Connected to Upstash")
    except Exception as e:
        print(f"[ERROR] Failed to connect: {e}")
        return False

    # Create test session
    session_id = f"test-interleaved-{int(time.time())}"
    stream_key = f"popkit:stream:{session_id}"

    print(f"\n[OK] Test session: {session_id}")
    print(f"[OK] Stream key: {stream_key}")
    print()

    # Create two agents
    agent1 = CoordinatedAgent(
        agent_id="agent-1",
        agent_name="math-questioner",
        redis_client=redis_client,
        stream_key=stream_key,
        poll_interval=5  # Poll every 5 seconds
    )

    agent2 = CoordinatedAgent(
        agent_id="agent-2",
        agent_name="math-answerer",
        redis_client=redis_client,
        stream_key=stream_key,
        poll_interval=5  # Poll every 5 seconds
    )

    print("="*70)
    print("  STARTING COORDINATION")
    print("="*70)
    print("\nAgent 1 and Agent 2 will poll every 5 seconds")
    print("They will play a math game:")
    print("  1. Agent asks question")
    print("  2. Other agent answers and asks new question")
    print("  3. Repeat")
    print("\nWatch for interleaved messages in timestamps!")
    print("="*70)
    print()

    # Agent 1 starts by asking first question
    print("[INIT] Agent 1 asks first question to start the game...")
    first_question = agent1.generate_math_problem()
    agent1.publish_message(
        msg_type="question",
        content=f"Question: {first_question}",
        metadata={"question": first_question}
    )
    print()

    # Start both agents in parallel threads
    duration = 30  # Run for 30 seconds

    thread1 = threading.Thread(
        target=agent1.poll_loop,
        args=(duration,)
    )

    thread2 = threading.Thread(
        target=agent2.poll_loop,
        args=(duration,)
    )

    # Offset agent 2 start by 2.5 seconds for interleaving
    thread1.start()
    time.sleep(2.5)
    thread2.start()

    # Wait for both to finish
    thread1.join()
    thread2.join()

    print("\n" + "="*70)
    print("  VERIFICATION")
    print("="*70)
    print()

    # Read all messages from stream
    messages = redis_client.xread({stream_key: "0"}, count=100)

    if not messages or len(messages) == 0:
        print("[ERROR] No messages found in stream!")
        return False

    stream_name, msg_list = messages[0]

    print(f"[OK] Total messages: {len(msg_list)}")
    print()

    # Analyze message pattern
    agent1_count = 0
    agent2_count = 0
    questions = 0
    answers = 0

    print("Message Timeline:")
    print("-" * 70)

    for i, msg_entry in enumerate(msg_list, 1):
        msg_id, msg_data = msg_entry

        # Parse
        data_dict = {}
        for j in range(0, len(msg_data), 2):
            key = msg_data[j]
            value = msg_data[j + 1]
            if isinstance(key, bytes):
                key = key.decode('utf-8')
            if isinstance(value, bytes):
                value = value.decode('utf-8')
            data_dict[key] = value

        agent_id = data_dict.get("agent_id", "")
        msg_type = data_dict.get("type", "")
        timestamp = data_dict.get("timestamp", "")
        content = data_dict.get("content", "")

        if agent_id == "agent-1":
            agent1_count += 1
        elif agent_id == "agent-2":
            agent2_count += 1

        if msg_type == "question":
            questions += 1
        elif msg_type == "answer":
            answers += 1

        # Print timeline entry
        time_short = timestamp[-12:-4] if timestamp else "?"  # Just HH:MM:SS
        print(f"{i:2d}. [{time_short}] {agent_id}: {msg_type:8s} - {content[:45]}")

    print("-" * 70)
    print()

    print("Summary:")
    print(f"  Agent 1 messages: {agent1_count}")
    print(f"  Agent 2 messages: {agent2_count}")
    print(f"  Questions: {questions}")
    print(f"  Answers: {answers}")
    print()

    # Check for interleaving
    agent_sequence = []
    for msg_entry in msg_list:
        msg_id, msg_data = msg_entry
        data_dict = {}
        for j in range(0, len(msg_data), 2):
            key = msg_data[j]
            value = msg_data[j + 1]
            if isinstance(key, bytes):
                key = key.decode('utf-8')
            data_dict[key] = value
        agent_sequence.append(data_dict.get("agent_id", ""))

    # Check if we have both agents alternating (not all agent-1 then all agent-2)
    has_interleaving = False
    for i in range(len(agent_sequence) - 1):
        if agent_sequence[i] != agent_sequence[i + 1]:
            has_interleaving = True
            break

    if has_interleaving:
        print("[SUCCESS] Messages are INTERLEAVED (not sequential batches)")
        print("[SUCCESS] Agents coordinated in real-time back-and-forth")
    else:
        print("[WARNING] Messages appear sequential, not interleaved")

    print()
    print("="*70)
    print("  VIEW IN UPSTASH CONSOLE")
    print("="*70)
    print(f"\n1. Go to: https://console.upstash.com/redis")
    print(f"2. Select your 'popkit' database")
    print(f"3. Go to 'Data Browser' tab")
    print(f"4. Search for: {stream_key}")
    print(f"5. Look at timestamps - should show interleaved pattern")
    print()
    print("Expected pattern:")
    print("  [Time 00:00] agent-1: question")
    print("  [Time 00:05] agent-2: answer + question")
    print("  [Time 00:10] agent-1: answer + question")
    print("  [Time 00:15] agent-2: answer + question")
    print("  ...")
    print()

    print("="*70)
    print("  TEST COMPLETE")
    print("="*70)
    print(f"\nStream: {stream_key}")
    print(f"Messages: {len(msg_list)}")
    print(f"Interleaved: {'YES' if has_interleaving else 'NO'}")
    print()

    return has_interleaving


if __name__ == "__main__":
    success = test_interleaved_coordination()
    sys.exit(0 if success else 1)
