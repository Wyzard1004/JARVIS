"""
JARVIS Demo Soldier Controller (Section 2.5.0)

Puppetable soldier system that demonstrates the command routing pipeline:

COMMAND ROUTES:
  1. Soldier -> Operator -> Attack     (Request approval for strike)
  2. Soldier -> Operator -> Recon      (Request surveillance)
  3. Recon -> Operator -> Attack       (Report detection, request strike authorization)
  4. Soldier -> Attack                 (Direct strike command)
  5. Soldier -> Recon                  (Direct reconnaissance command)

WORKFLOW:
  1. Soldier receives tactical objective
  2. Soldier requests operator authorization for reconnaissance
  3. Recon drone scans area, identifies targets
  4. Recon reports findings back through operator
  5. Soldier/Operator authorizes strike
  6. Attack drones engage targets
  7. Recon confirms BDA (Battle Damage Assessment)
"""

from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum
import random


class CommandPriority(Enum):
    """Command priority levels for routing."""
    CRITICAL = 3     # Immediate threat response
    HIGH = 2         # Tactical directive from soldier
    MEDIUM = 1       # Routine reconnaissance
    LOW = 0          # Informational


class CommandRoute(Enum):
    """Valid command routing paths."""
    SOLDIER_TO_OPERATOR_TO_ATTACK = "soldier→operator→attack"
    SOLDIER_TO_OPERATOR_TO_RECON = "soldier→operator→recon"
    RECON_TO_OPERATOR_TO_ATTACK = "recon→operator→attack"
    SOLDIER_TO_ATTACK_DIRECT = "soldier→attack"
    SOLDIER_TO_RECON_DIRECT = "soldier→recon"


class SoldierControllerNode:
    """
    Represents a soldier node that can be puppeted.
    Controls the command routing pipeline to drones.
    """

    def __init__(self, soldier_id: str, operator_node_id: str = "soldier-1"):
        self.soldier_id = soldier_id
        self.operator_node_id = operator_node_id
        self.active_missions: Dict[str, Dict] = {}
        self.command_log: List[Dict] = []
        self.recon_reports: Dict[str, Dict] = {}
        self.authorized_targets: set = set()
        self.status = "ready"
        self.last_command_time = None

    def request_reconnaissance(
        self,
        area_label: str,
        target_x: float,
        target_y: float,
        priority: CommandPriority = CommandPriority.HIGH,
    ) -> Dict:
        """
        ROUTE: Soldier -> Operator -> Recon
        
        Soldier requests operator authorization for reconnaissance.
        Operator relays command to recon drone.
        """
        command = {
            "command_id": f"{self.soldier_id}-recon-{len(self.command_log)}",
            "type": "reconnaissance",
            "route": CommandRoute.SOLDIER_TO_OPERATOR_TO_RECON.value,
            "originator": self.soldier_id,
            "operator": self.operator_node_id,
            "target_drone": "recon-1",
            "area_label": area_label,
            "target_x": target_x,
            "target_y": target_y,
            "priority": priority.name,
            "status": "pending_operator_approval",
            "created_at": datetime.now().isoformat(),
            "operator_approved_at": None,
            "mission_id": None,
        }
        
        self.command_log.append(command)
        self.active_missions[command["command_id"]] = command
        return command

    def request_attack(
        self,
        area_label: str,
        target_x: float,
        target_y: float,
        priority: CommandPriority = CommandPriority.HIGH,
        requires_approval: bool = True,
    ) -> Dict:
        """
        ROUTE: Soldier -> Operator -> Attack (if requires_approval=True)
               Soldier -> Attack (if requires_approval=False)
        
        Soldier requests attack authorization through operator,
        or issues direct attack command.
        """
        route = (
            CommandRoute.SOLDIER_TO_OPERATOR_TO_ATTACK.value
            if requires_approval
            else CommandRoute.SOLDIER_TO_ATTACK_DIRECT.value
        )
        
        command = {
            "command_id": f"{self.soldier_id}-attack-{len(self.command_log)}",
            "type": "attack",
            "route": route,
            "originator": self.soldier_id,
            "operator": self.operator_node_id if requires_approval else None,
            "target_drones": ["attack-1", "attack-2"],
            "area_label": area_label,
            "target_x": target_x,
            "target_y": target_y,
            "priority": priority.name,
            "status": "pending_operator_approval" if requires_approval else "authorized",
            "created_at": datetime.now().isoformat(),
            "operator_approved_at": None,
            "mission_id": None,
            "requires_approval": requires_approval,
        }
        
        self.command_log.append(command)
        self.active_missions[command["command_id"]] = command
        return command

    def approve_and_relay_command(self, command_id: str) -> Dict:
        """
        Operator approves command and relays to appropriate drone(s).
        Updates command status and establishes mission tracking.
        """
        if command_id not in self.active_missions:
            return {"error": f"Command {command_id} not found"}

        command = self.active_missions[command_id]
        command["status"] = "authorized"
        command["operator_approved_at"] = datetime.now().isoformat()
        command["mission_id"] = f"mission-{command_id[-8:]}"

        return {
            "approved": True,
            "command_id": command_id,
            "mission_id": command["mission_id"],
            "route": command["route"],
            "target_drones": command.get("target_drones"),
            "target_location": command.get("area_label"),
            "approved_at": command["operator_approved_at"],
        }

    def process_recon_report(
        self,
        mission_id: str,
        enemies_detected: List[Dict],
        coverage_percent: float,
        threat_level: str,
    ) -> Dict:
        """
        Recon drone reports findings back through operator.
        
        ROUTE: Recon -> Operator -> Soldier
        
        Soldier can then authorize attack based on threat assessment.
        """
        report = {
            "report_id": f"recon-report-{len(self.recon_reports)}",
            "mission_id": mission_id,
            "submitter": "recon-1",
            "receiver": self.operator_node_id,
            "final_recipient": self.soldier_id,
            "enemies_detected": enemies_detected,
            "coverage_percent": coverage_percent,
            "threat_level": threat_level,
            "assessment_time": datetime.now().isoformat(),
            "bda_ready": False,
            "status": "awaiting_authorization",
        }

        self.recon_reports[report["report_id"]] = report
        return report

    def authorize_strike_from_recon_report(
        self, recon_report_id: str, priority: CommandPriority = CommandPriority.CRITICAL
    ) -> Dict:
        """
        ROUTE: Recon -> Operator -> Attack
        (with Soldier authorization)
        
        Based on recon findings, soldier authorizes strike.
        Operator relays to attack drones.
        """
        if recon_report_id not in self.recon_reports:
            return {"error": f"Recon report {recon_report_id} not found"}

        report = self.recon_reports[recon_report_id]
        enemies = report["enemies_detected"]

        command = {
            "command_id": f"{self.soldier_id}-authorized-strike-{len(self.command_log)}",
            "type": "attack",
            "route": CommandRoute.RECON_TO_OPERATOR_TO_ATTACK.value,
            "originator": self.soldier_id,
            "operator": self.operator_node_id,
            "recon_report_id": recon_report_id,
            "target_drones": ["attack-1", "attack-2"],
            "enemies_to_engage": enemies,
            "threat_level": report["threat_level"],
            "priority": priority.name,
            "status": "authorized",
            "created_at": datetime.now().isoformat(),
            "operator_approved_at": datetime.now().isoformat(),
            "mission_id": f"mission-strike-{recon_report_id[-8:]}",
        }

        self.command_log.append(command)
        self.active_missions[command["command_id"]] = command
        return command

    def process_bda_report(
        self, mission_id: str, damage_assessment: Dict
    ) -> Dict:
        """
        Process Battle Damage Assessment from recon drone.
        
        Tracks targets destroyed/damaged and updates mission status.
        """
        bda = {
            "bda_id": f"bda-{len(self.recon_reports)}",
            "mission_id": mission_id,
            "submitter": "recon-1",
            "damage_assessment": damage_assessment,
            "assessment_time": datetime.now().isoformat(),
            "status": "complete",
        }

        # Update recon reports with BDA
        for report_id, report in self.recon_reports.items():
            if report.get("mission_id") == mission_id:
                report["bda_ready"] = True
                report["bda"] = bda
                break

        return bda

    def get_mission_status(self, mission_id: str) -> Dict:
        """Get current status of an active mission."""
        for cmd_id, cmd in self.active_missions.items():
            if cmd.get("mission_id") == mission_id:
                return {
                    "mission_id": mission_id,
                    "command_id": cmd_id,
                    "type": cmd["type"],
                    "route": cmd["route"],
                    "status": cmd["status"],
                    "created_at": cmd["created_at"],
                    "target_location": cmd.get("area_label"),
                    "drones_assigned": cmd.get("target_drones"),
                }

        return {"error": f"Mission {mission_id} not found"}

    def get_command_summary(self) -> Dict:
        """Get summary of all commands and missions."""
        return {
            "soldier_id": self.soldier_id,
            "status": self.status,
            "total_commands": len(self.command_log),
            "active_missions": len(self.active_missions),
            "recon_reports": len(self.recon_reports),
            "authorized_targets": len(self.authorized_targets),
            "commands": [
                {
                    "id": cmd["command_id"],
                    "type": cmd["type"],
                    "route": cmd["route"],
                    "status": cmd["status"],
                    "priority": cmd.get("priority"),
                    "created_at": cmd["created_at"],
                }
                for cmd in self.command_log[-10:]  # Last 10 commands
            ],
            "recent_recon_reports": [
                {
                    "id": rep["report_id"],
                    "enemies_detected": len(rep["enemies_detected"]),
                    "threat_level": rep["threat_level"],
                    "assessment_time": rep["assessment_time"],
                }
                for rep in list(self.recon_reports.values())[-5:]  # Last 5 reports
            ],
        }

    def simulate_tactical_scenario(self, grid_area: str) -> Dict:
        """
        Simulate a complete tactical scenario:
        1. Soldier requests reconnaissance
        2. Recon drone scans area
        3. Enemies detected
        4. Soldier authorizes strike
        5. Attack drones engage
        6. Recon confirms BDA
        """
        scenario = {
            "scenario_id": f"scenario-{len(self.command_log)}",
            "area": grid_area,
            "stages": [],
        }

        # Stage 1: Request reconnaissance
        recon_request = self.request_reconnaissance(
            area_label=grid_area,
            target_x=random.randint(0, 1000),
            target_y=random.randint(-300, 300),
            priority=CommandPriority.HIGH,
        )
        scenario["stages"].append(
            {
                "stage": "recon_request",
                "command_id": recon_request["command_id"],
                "description": "Soldier requests reconnaissance via operator",
            }
        )

        # Stage 2: Operator approves
        approval = self.approve_and_relay_command(recon_request["command_id"])
        scenario["stages"].append(
            {"stage": "operator_approval", "mission_id": approval["mission_id"]}
        )

        # Stage 3: Recon findings
        enemies = [
            {"id": f"enemy-{i}", "type": "vehicle", "threat_level": "high", "x": random.randint(-100, 100), "y": random.randint(-100, 100)}
            for i in range(random.randint(2, 4))
        ]
        recon_report = self.process_recon_report(
            mission_id=approval["mission_id"],
            enemies_detected=enemies,
            coverage_percent=random.randint(75, 95),
            threat_level="high",
        )
        scenario["stages"].append(
            {
                "stage": "recon_findings",
                "report_id": recon_report["report_id"],
                "enemies_count": len(enemies),
            }
        )

        # Stage 4: Strike authorization
        strike = self.authorize_strike_from_recon_report(
            recon_report_id=recon_report["report_id"],
            priority=CommandPriority.CRITICAL,
        )
        scenario["stages"].append(
            {
                "stage": "strike_authorization",
                "command_id": strike["command_id"],
                "drones": strike["target_drones"],
            }
        )

        # Stage 5: BDA
        bda = self.process_bda_report(
            mission_id=strike["mission_id"],
            damage_assessment={
                "targets_engaged": len(enemies),
                "destroyed": random.randint(int(len(enemies) * 0.5), len(enemies)),
                "damaged": random.randint(0, int(len(enemies) * 0.5)),
                "escaped": random.randint(0, 1),
            },
        )
        scenario["stages"].append(
            {
                "stage": "bda_report",
                "bda_id": bda["bda_id"],
                "damage": bda["damage_assessment"],
            }
        )

        scenario["status"] = "complete"
        return scenario
