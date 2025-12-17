#!/usr/bin/env python3
"""
Puzzle Coordination Test

Tests if agents naturally coordinate when they need each other's information.

Scenario: Security Incident Investigation
- Both agents are investigating the same security breach
- Each has SECRET context (log data vs code knowledge)
- Neither knows the other has the complementary piece
- They check in periodically about progress
- Will they naturally share insights to solve it together?

The puzzle is UNSOLVABLE without combining both agents' information.
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


# Define the puzzle pieces (secrets each agent knows)
AGENT_1_SECRET_CONTEXT = """
BACKGROUND CONTEXT:
You're investigating a security incident that occurred on 2025-12-17.

SYSTEM LOGS (your only information source):
- 03:42:15 - Failed login attempt for user 'admin' from IP 192.168.1.47
- 03:42:18 - Failed login attempt for user 'admin' from IP 192.168.1.47
- 03:42:23 - Successful login for user 'admin' from IP 192.168.1.47
- 03:43:10 - Database backup initiated by user 'admin'
- 03:44:55 - Large data export (2.5 GB) to external endpoint 45.33.21.108
- 03:45:12 - User 'admin' logged out

This seems suspicious but you need to understand HOW they got in.
"""

AGENT_2_SECRET_CONTEXT = """
BACKGROUND CONTEXT:
You're reviewing the authentication system for security issues.

CODE REVIEW FINDINGS (your only information source):
- Login rate limiting: Maximum 3 attempts per 60 seconds per IP
- Account lockout: Account locks for 15 minutes after 3 failed attempts
- Password policy: Minimum 8 characters, enforced
- Known bug (found in code): Rate limiter has a flaw where it resets the counter
  if requests come from the same IP but with different User-Agent headers
- This bug was reported but not yet patched

You suspect this bug might be exploitable but need evidence it was used.
"""

SHARED_TASK = """
TASK: Determine what security vulnerability was exploited and how the attacker gained access.

INSTRUCTIONS:
- Analyze the information available to you
- Check in periodically with your progress/findings (high-level, 1-2 sentences)
- You're working independently but may collaborate if helpful
- Solve the puzzle: What vulnerability was used and how?
"""


class PuzzleAgent:
    """Agent with secret context working to solve a puzzle."""

    def __init__(self, agent_id, agent_name, secret_context, task, redis_client, stream_key, poll_interval=10):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.secret_context = secret_context  # Only this agent knows this
        self.task = task  # The shared goal
        self.redis_client = redis_client
        self.stream_key = stream_key
        self.poll_interval = poll_interval
        self.processed_message_ids = set()
        self.running = False
        self.message_count = 0
        self.check_in_count = 0
        self.solved = False
        self.solution = None

        # Agent's "thought process" - what they've figured out
        self.findings = []
        self.stuck_on = None

    def publish_check_in(self, message):
        """Publish a check-in message to the stream."""
        self.check_in_count += 1

        msg_data = {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "type": "check_in",
            "check_in_num": str(self.check_in_count),
            "message": message,
            "timestamp": datetime.now().isoformat()
        }

        msg_id = self.redis_client.xadd(self.stream_key, msg_data)
        self.message_count += 1

        print(f"[{self.agent_id}] Check-in #{self.check_in_count}: {message}")
        return msg_id

    def publish_question(self, question):
        """Ask a question to other agents."""
        msg_data = {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "type": "question",
            "question": question,
            "timestamp": datetime.now().isoformat()
        }

        msg_id = self.redis_client.xadd(self.stream_key, msg_data)
        self.message_count += 1

        print(f"[{self.agent_id}] Question: {question}")
        return msg_id

    def publish_answer(self, answer, responding_to):
        """Answer another agent's question."""
        msg_data = {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "type": "answer",
            "answer": answer,
            "responding_to": responding_to,
            "timestamp": datetime.now().isoformat()
        }

        msg_id = self.redis_client.xadd(self.stream_key, msg_data)
        self.message_count += 1

        print(f"[{self.agent_id}] Answer: {answer[:80]}...")
        return msg_id

    def publish_solution(self, solution):
        """Publish the final solution."""
        msg_data = {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "type": "solution",
            "solution": solution,
            "timestamp": datetime.now().isoformat()
        }

        msg_id = self.redis_client.xadd(self.stream_key, msg_data)
        self.message_count += 1
        self.solved = True
        self.solution = solution

        print(f"[{self.agent_id}] SOLUTION: {solution}")
        return msg_id

    def read_stream(self):
        """Read new messages from stream."""
        try:
            msg_list = self.redis_client.xrange(
                self.stream_key,
                min="-",
                max="+",
                count=100
            )

            if not msg_list:
                return []

            # Parse and filter new messages
            new_messages = []
            for msg_entry in msg_list:
                msg_id, msg_data = msg_entry

                # Skip if already processed
                if msg_id in self.processed_message_ids:
                    continue

                self.processed_message_ids.add(msg_id)

                # Convert to dict
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
                    new_messages.append(data_dict)

            return new_messages

        except Exception as e:
            print(f"[{self.agent_id}] Error reading stream: {e}")
            return []

    def analyze_own_context(self):
        """Analyze what this agent knows from their secret context."""
        # This simulates agent thinking about their own information

        if self.agent_id == "agent-1":
            # Agent 1 has logs
            self.findings = [
                "I see 3 login attempts, with the 3rd succeeding",
                "After successful login, suspicious activity occurred (backup, large export)",
                "All from same IP: 192.168.1.47",
                "Timeline is tight: attack happened quickly"
            ]
            self.stuck_on = "How did they get past rate limiting and lockout after 2 failures?"

        elif self.agent_id == "agent-2":
            # Agent 2 has code knowledge
            self.findings = [
                "System has rate limiting (3 attempts per minute)",
                "Accounts lock after 3 failed attempts",
                "Found a bug: rate limiter resets if User-Agent changes",
                "This could allow unlimited attempts by cycling User-Agent"
            ]
            self.stuck_on = "Do we have evidence this bug was actually exploited?"

    def decide_next_action(self, iteration):
        """Decide what to do next based on current state."""

        # First iteration: analyze own context and share WHAT I'M DOING
        if iteration == 1:
            self.analyze_own_context()
            if self.agent_id == "agent-1":
                return ("check_in", "Starting log analysis. Reviewing system logs from 2025-12-17 incident window.")
            elif self.agent_id == "agent-2":
                return ("check_in", "Starting code review. Analyzing authentication and rate limiting implementation.")

        # Second iteration: share first finding from MY work
        if iteration == 2:
            if len(self.findings) > 0:
                return ("check_in", f"Found: {self.findings[0]}")
            return ("check_in", "Analysis in progress...")

        # Third iteration: share what I'M stuck on in MY work
        if iteration == 3 and not self.solved:
            if self.stuck_on:
                return ("check_in", f"Working on: {self.stuck_on[:80]}")
            else:
                return ("check_in", "Making progress on my analysis...")

        # Fourth iteration: might ask question if REALLY stuck
        if iteration == 4 and not self.solved and self.stuck_on:
            if self.agent_id == "agent-1":
                return ("question", "Does anyone know if there are ways to bypass the rate limiter?")
            elif self.agent_id == "agent-2":
                return ("question", "Has anyone seen evidence of multiple failed logins from the same source?")

        # Later iterations: continue sharing MY progress
        if iteration >= 5 and not self.solved:
            if iteration == 5:
                if len(self.findings) > 1:
                    return ("check_in", f"Additional finding: {self.findings[1]}")
            return ("check_in", "Continuing my investigation...")

        return None

    def process_message(self, message):
        """Process a message from another agent."""
        msg_type = message.get("type", "")
        from_agent = message.get("agent_id", "")

        if msg_type == "check_in":
            check_in_msg = message.get("message", "")
            print(f"[{self.agent_id}] Read from {from_agent}: {check_in_msg}")

            # Analyze if this helps us
            if self.agent_id == "agent-1":
                # Agent 1 learns about rate limiter bug
                if "rate limiter" in check_in_msg.lower() and "user-agent" in check_in_msg.lower():
                    print(f"[{self.agent_id}] INSIGHT: This explains how they bypassed lockout!")
                    self.findings.append("Other agent found rate limiter bug with User-Agent switching")
                    self.stuck_on = None

            elif self.agent_id == "agent-2":
                # Agent 2 learns about failed logins
                if "3 login" in check_in_msg.lower() or "failed" in check_in_msg.lower():
                    print(f"[{self.agent_id}] INSIGHT: Evidence the bug was exploited!")
                    self.findings.append("Other agent has logs showing pattern matching the bug")
                    self.stuck_on = None

        elif msg_type == "question":
            question = message.get("question", "")
            print(f"[{self.agent_id}] Question from {from_agent}: {question}")

            # Try to answer based on our secret knowledge
            if self.agent_id == "agent-1" and "failed login" in question.lower():
                # Share relevant log info
                time.sleep(1)
                self.publish_answer(
                    "Yes, I see 2 failed login attempts followed by success, all from same IP within 8 seconds",
                    from_agent
                )

            elif self.agent_id == "agent-2" and "rate limiter" in question.lower():
                # Share code bug info
                time.sleep(1)
                self.publish_answer(
                    "Yes, there's a known bug where rate limiter resets if User-Agent header changes per request",
                    from_agent
                )

        elif msg_type == "answer":
            answer = message.get("answer", "")
            print(f"[{self.agent_id}] Answer from {from_agent}: {answer}")

            # This might solve our puzzle!
            if not self.solved:
                # Check if we now have enough to solve it
                combined_knowledge = len([f for f in self.findings if "other agent" in f.lower()]) > 0

                if combined_knowledge and self.stuck_on is None:
                    # We have both pieces!
                    time.sleep(2)
                    solution = (
                        "SOLVED: Attacker exploited rate limiter bug by changing User-Agent header "
                        "between failed attempts, bypassing lockout. This allowed brute-force attack "
                        "that succeeded on 3rd attempt, then exfiltrated data."
                    )
                    self.publish_solution(solution)

    def work_loop(self, duration_seconds=60, max_iterations=6):
        """Main work loop - analyze, check in, coordinate."""
        self.running = True
        start_time = time.time()
        iteration = 0

        print(f"[{self.agent_id}] Starting investigation...")
        print(f"[{self.agent_id}] Secret context: {self.secret_context[:100]}...")
        print()

        while self.running and iteration < max_iterations and not self.solved:
            iteration += 1
            elapsed = time.time() - start_time

            if elapsed >= duration_seconds:
                break

            # Decide what to do this iteration
            action = self.decide_next_action(iteration)

            if action:
                action_type, action_data = action

                if action_type == "check_in":
                    self.publish_check_in(action_data)
                elif action_type == "question":
                    self.publish_question(action_data)

            # Read stream and process messages
            time.sleep(1)  # Small delay before reading
            messages = self.read_stream()

            for msg in messages:
                self.process_message(msg)

            # Wait for next poll
            time.sleep(self.poll_interval)

        print(f"[{self.agent_id}] Investigation ended (solved={self.solved})")
        self.running = False


def test_puzzle_coordination():
    """Test if agents naturally coordinate to solve a puzzle."""
    print("\n" + "="*70)
    print("  PUZZLE COORDINATION TEST")
    print("="*70)
    print(f"Started: {datetime.now().isoformat()}")
    print()

    print("SCENARIO: Security Incident Investigation")
    print()
    print("Agent 1 has: System logs showing attack timeline")
    print("Agent 2 has: Code with rate limiter bug details")
    print()
    print("Both are tasked: Figure out how attacker gained access")
    print("Neither knows: The other has complementary information")
    print()
    print("Will they naturally coordinate to solve it?")
    print("="*70)
    print()

    # Check Upstash
    if not is_upstash_available():
        print("[ERROR] Upstash Redis not configured")
        return False

    print("[OK] Upstash Redis credentials found")

    try:
        redis_client = get_redis_client()
        print(f"[OK] Connected to Upstash")
    except Exception as e:
        print(f"[ERROR] Failed to connect: {e}")
        return False

    # Create test session
    session_id = f"test-puzzle-{int(time.time())}"
    stream_key = f"popkit:stream:{session_id}"

    print(f"\n[OK] Test session: {session_id}")
    print(f"[OK] Stream key: {stream_key}")
    print()

    # Create two agents with different secret contexts
    agent1 = PuzzleAgent(
        agent_id="agent-1",
        agent_name="log-analyzer",
        secret_context=AGENT_1_SECRET_CONTEXT,
        task=SHARED_TASK,
        redis_client=redis_client,
        stream_key=stream_key,
        poll_interval=10
    )

    agent2 = PuzzleAgent(
        agent_id="agent-2",
        agent_name="code-reviewer",
        secret_context=AGENT_2_SECRET_CONTEXT,
        task=SHARED_TASK,
        redis_client=redis_client,
        stream_key=stream_key,
        poll_interval=10
    )

    print("="*70)
    print("  STARTING INVESTIGATION")
    print("="*70)
    print()

    duration = 60  # 60 seconds

    # Start both agents
    thread1 = threading.Thread(target=agent1.work_loop, args=(duration,))
    thread2 = threading.Thread(target=agent2.work_loop, args=(duration,))

    thread1.start()
    time.sleep(2)  # Slight offset
    thread2.start()

    # Wait for completion
    thread1.join()
    thread2.join()

    print("\n" + "="*70)
    print("  RESULTS")
    print("="*70)
    print()

    # Check if puzzle was solved
    solved_by = []
    if agent1.solved:
        solved_by.append(f"Agent 1: {agent1.solution}")
    if agent2.solved:
        solved_by.append(f"Agent 2: {agent2.solution}")

    print(f"Puzzle solved: {len(solved_by) > 0}")
    if solved_by:
        print()
        for solution in solved_by:
            print(f"  {solution[:100]}...")

    # Analyze coordination
    messages = redis_client.xread({stream_key: "0"}, count=100)

    if messages and len(messages) > 0:
        stream_name, msg_list = messages[0]

        check_ins = 0
        questions = 0
        answers = 0
        solutions = 0

        print(f"\nTotal messages: {len(msg_list)}")
        print("\nMessage breakdown:")

        for msg_entry in msg_list:
            msg_id, msg_data = msg_entry
            data_dict = {}
            for i in range(0, len(msg_data), 2):
                key = msg_data[i]
                value = msg_data[i + 1]
                if isinstance(key, bytes):
                    key = key.decode('utf-8')
                if isinstance(value, bytes):
                    value = value.decode('utf-8')
                data_dict[key] = value

            msg_type = data_dict.get("type", "")
            if msg_type == "check_in":
                check_ins += 1
            elif msg_type == "question":
                questions += 1
            elif msg_type == "answer":
                answers += 1
            elif msg_type == "solution":
                solutions += 1

        print(f"  Check-ins: {check_ins}")
        print(f"  Questions: {questions}")
        print(f"  Answers: {answers}")
        print(f"  Solutions: {solutions}")

        # Success criteria
        coordinated = questions > 0 and answers > 0

        print()
        if len(solved_by) > 0 and coordinated:
            print("[SUCCESS] Agents coordinated naturally and solved the puzzle!")
        elif len(solved_by) > 0:
            print("[PARTIAL] Puzzle solved but minimal coordination occurred")
        elif coordinated:
            print("[PARTIAL] Agents coordinated but didn't solve puzzle")
        else:
            print("[FAILED] No meaningful coordination occurred")

    print()
    print("="*70)
    print("  VIEW IN UPSTASH CONSOLE")
    print("="*70)
    print(f"\nStream: {stream_key}")
    print("Look for:")
    print("  - Check-in messages showing progress")
    print("  - Questions between agents")
    print("  - Answers sharing secret information")
    print("  - Solution message (if puzzle was solved)")
    print()

    return len(solved_by) > 0


if __name__ == "__main__":
    success = test_puzzle_coordination()
    sys.exit(0 if success else 1)
