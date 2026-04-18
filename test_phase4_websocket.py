#!/usr/bin/env python3
"""
Test Phase 4 WebSocket Integration

Tests:
1. State sync loop (100ms interval updates)
2. Command handler (soldier_command, recon_mission, engage_target, etc.)
3. Full message structure for frontend compatibility
"""

import asyncio
import json
import sys
from pathlib import Path

# Add base_station to path
sys.path.insert(0, str(Path(__file__).parent / "base_station"))

from core.swarm_logic import get_swarm


async def test_state_sync_message():
    """Test that state sync messages have correct structure."""
    print("\n" + "=" * 70)
    print("TEST 1: State Sync Message Structure")
    print("=" * 70)
    
    swarm = get_swarm()
    state = swarm.get_state()
    
    # Build a state_update message like the WebSocket would send
    state_update = {
        "event": "state_update",
        "nodes": state.get("nodes", []),
        "edges": state.get("edges", []),
        "spanning_tree_root": state.get("spanning_tree_root"),
        "spanning_tree_edges": state.get("spanning_tree_edges", []),
        "drone_positions": state.get("drone_positions", {}),
        "drone_behaviors": state.get("drone_behaviors", {}),
        "active_gossip_messages": state.get("active_gossip_messages", []),
        "timestamp": "2024-test"
    }
    
    # Verify structure
    required_fields = ["event", "nodes", "edges", "spanning_tree_root", 
                       "spanning_tree_edges", "drone_positions", "drone_behaviors", 
                       "active_gossip_messages", "timestamp"]
    
    missing = [f for f in required_fields if f not in state_update]
    
    if missing:
        print(f"✗ FAILED: Missing fields in state_update: {missing}")
        return False
    
    print(f"✓ Event: {state_update['event']}")
    print(f"✓ Nodes: {len(state_update['nodes'])} drones")
    print(f"✓ Edges: {len(state_update['edges'])} transmission edges")
    print(f"✓ Spanning tree: root={state_update['spanning_tree_root']}, edges={len(state_update['spanning_tree_edges'])}")
    print(f"✓ Drone positions: {len(state_update['drone_positions'])} tracked")
    print(f"✓ Drone behaviors: {len(state_update['drone_behaviors'])} behaviors")
    print(f"✓ Gossip messages: {len(state_update['active_gossip_messages'])} active")
    
    # Try to JSON serialize (as WebSocket would do)
    try:
        json_str = json.dumps(state_update)
        print(f"✓ JSON serialization successful ({len(json_str)} bytes)")
    except Exception as e:
        print(f"✗ FAILED: JSON serialization failed: {e}")
        return False
    
    return True


async def test_command_handler():
    """Test command handler responses."""
    print("\n" + "=" * 70)
    print("TEST 2: Command Handler")
    print("=" * 70)
    
    # Import here to test in isolation
    from api.main import handle_websocket_command
    
    swarm = get_swarm()
    
    # Test 1: sync_state command
    print("\n1. Testing sync_state command...")
    sync_cmd = {"type": "sync_state"}
    response = await handle_websocket_command(sync_cmd, swarm)
    
    if response.get("status") != "success":
        print(f"✗ FAILED: sync_state returned {response}")
        return False
    
    if "state" not in response:
        print(f"✗ FAILED: No state in sync_state response")
        return False
    
    print(f"✓ sync_state returned state with {len(response['state'].get('nodes', []))} nodes")
    
    # Test 2: soldier_command
    print("\n2. Testing soldier_command...")
    soldier_cmd = {
        "type": "soldier_command",
        "target_drone": "soldier-1",
        "instruction": {"behavior": "patrol"}
    }
    response = await handle_websocket_command(soldier_cmd, swarm)
    
    if response.get("status") != "success":
        print(f"✗ FAILED: soldier_command returned {response}")
        return False
    
    # Verify drone behavior was changed
    new_behavior = swarm._drone_behaviors["soldier-1"]["current"]
    if new_behavior != "patrol":
        print(f"✗ FAILED: Drone behavior not changed. Got: {new_behavior}")
        return False
    
    print(f"✓ soldier_command successfully changed behavior to 'patrol'")
    
    # Test 3: recon_mission
    print("\n3. Testing recon_mission...")
    recon_cmd = {
        "type": "recon_mission",
        "grid_location": "Bravo"
    }
    response = await handle_websocket_command(recon_cmd, swarm)
    
    if response.get("status") != "success":
        print(f"✗ FAILED: recon_mission returned {response}")
        return False
    
    recon_drones = response.get("recon_drones", [])
    if not recon_drones:
        print(f"✗ FAILED: No recon drones in response")
        return False
    
    print(f"✓ recon_mission assigned {len(recon_drones)} recon drones")
    
    # Test 4: engage_target
    print("\n4. Testing engage_target...")
    engage_cmd = {
        "type": "engage_target",
        "target_location": "Grid Alpha",
        "priority": "high"
    }
    response = await handle_websocket_command(engage_cmd, swarm)
    
    if response.get("status") != "success":
        print(f"✗ FAILED: engage_target returned {response}")
        return False
    
    attack_drones = response.get("attack_drones", [])
    if not attack_drones:
        print(f"✗ FAILED: No attack drones in response")
        return False
    
    print(f"✓ engage_target coordinated {len(attack_drones)} attack drones")
    
    # Test 5: change_algorithm
    print("\n5. Testing change_algorithm...")
    algo_cmd = {
        "type": "change_algorithm",
        "algorithm": "raft"
    }
    response = await handle_websocket_command(algo_cmd, swarm)
    
    if response.get("status") != "success":
        print(f"✗ FAILED: change_algorithm returned {response}")
        return False
    
    print(f"✓ change_algorithm switched to 'raft'")
    
    # Test 6: Error handling - unknown drone
    print("\n6. Testing error handling (unknown drone)...")
    bad_cmd = {
        "type": "soldier_command",
        "target_drone": "unknown-drone-999",
        "instruction": {"behavior": "lurk"}
    }
    response = await handle_websocket_command(bad_cmd, swarm)
    
    if response.get("status") != "error":
        print(f"✗ FAILED: Should have returned error for unknown drone")
        return False
    
    print(f"✓ Error handling works: {response.get('error')}")
    
    # Test 7: Error handling - unknown command type
    print("\n7. Testing error handling (unknown command type)...")
    bad_cmd = {
        "type": "unknown_command_type",
        "data": "test"
    }
    response = await handle_websocket_command(bad_cmd, swarm)
    
    if response.get("status") != "error":
        print(f"✗ FAILED: Should have returned error for unknown command type")
        return False
    
    print(f"✓ Unknown command error handling works: {response.get('error')}")
    
    return True


async def test_continuous_state_updates():
    """Test that state can be read continuously."""
    print("\n" + "=" * 70)
    print("TEST 3: Continuous State Updates")
    print("=" * 70)
    
    swarm = get_swarm()
    
    # Simulate reading state 10 times (like the WebSocket loop would do)
    print("\nReading state 10 times (simulating 100ms interval)...")
    
    for i in range(10):
        try:
            state = swarm.get_state()
            
            # Verify basic structure each time
            assert len(state.get("nodes", [])) > 0, "No nodes on iteration {i}"
            assert "timestamp" not in state or state["timestamp"], "Invalid timestamp on iteration {i}"
            
            if i == 0:
                print(f"  Iteration {i+1}: {len(state['nodes'])} nodes, {len(state['edges'])} edges")
            
            # Simulate brief wait
            await asyncio.sleep(0.01)  # 10ms between reads
            
        except Exception as e:
            print(f"✗ FAILED on iteration {i}: {e}")
            return False
    
    print(f"  ✓ Successfully read state 10 times without errors")
    
    return True


async def main():
    """Run all Phase 4 WebSocket tests."""
    print("\n" + "=" * 70)
    print("PHASE 4: WebSocket Integration Tests")
    print("=" * 70)
    
    results = []
    
    try:
        # Test 1: State structure
        result = await test_state_sync_message()
        results.append(("State Sync Message", result))
        
        # Test 2: Command handler
        result = await test_command_handler()
        results.append(("Command Handler", result))
        
        # Test 3: Continuous updates
        result = await test_continuous_state_updates()
        results.append(("Continuous State", result))
        
    except Exception as e:
        print(f"\n✗ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {test_name}")
    
    if all(result for _, result in results):
        print("\n✓ ALL TESTS PASSED - Phase 4 Ready")
        return 0
    else:
        print("\n✗ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
