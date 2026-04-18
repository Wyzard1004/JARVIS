"""
Compute Drone Controller Module

Handles image processing pipeline:
Recon Drones send images -> Compute Drones process & analyze -> Attack Drones execute strikes

Compute drones perform:
1. Image reception from recon platforms
2. Target detection and classification
3. Threat assessment and priority ranking  
4. Strike authorization decision making
5. Attack coordination and targeting relay
"""

from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum
import json


class ThreatLevel(Enum):
    """Target threat classification"""
    CRITICAL = 5   # Command post, air defense, high-value target
    HIGH = 4       # Combat vehicles, armor formations
    MEDIUM = 3     # Logistics, support elements
    LOW = 2        # Personnel, civilian infrastructure
    UNKNOWN = 1    # Unclassified


class TargetType(Enum):
    """Classification of detected targets"""
    COMMAND_POST = "command-post"
    ARMOR = "armor"
    ANTI_AIR = "anti-air"
    PERSONNEL = "personnel"
    LOGISTICS = "logistics"
    INFRASTRUCTURE = "infrastructure"
    UNKNOWN = "unknown"


class AttackDecision(Enum):
    """Strike authorization decision"""
    AUTHORIZE = "authorize"
    HOLD = "hold"
    DENIED = "denied"
    NEEDS_CLARIFICATION = "needs-clarification"


class ComputeDroneController:
    """
    Compute drone for image processing and strike decision making.
    Acts as intelligent intermediary between recon sensors and attack platforms.
    """
    
    def __init__(self, drone_id: str, processor_capability: float = 0.95):
        """
        Initialize compute drone controller.
        
        Args:
            drone_id: Identifier (compute-1, compute-2)
            processor_capability: Processing quality metric (0.0-1.0)
        """
        self.drone_id = drone_id
        self.processor_capability = processor_capability
        self.status = "online"
        self.image_queue: List[Dict] = []
        self.processed_images: Dict[str, Dict] = {}
        self.target_database: Dict[str, Dict] = {}
        self.strike_decisions: Dict[str, Dict] = {}
        
    def receive_recon_image(
        self, 
        image_report_id: str,
        recon_drone_id: str,
        image_data: Dict,
        location_grid: str,
        timestamp: datetime = None
    ) -> Dict:
        """
        Receive and queue image from recon drone.
        
        Args:
            image_report_id: Unique identifier for this image
            recon_drone_id: Source recon drone ID
            image_data: Image metadata (resolution, quality, etc)
            location_grid: Grid area (e.g., "Grid Alpha 1")
            timestamp: Reception time
            
        Returns:
            Confirmation dict with processing status
        """
        if timestamp is None:
            timestamp = datetime.now()
            
        reception_record = {
            "reception_id": f"{self.drone_id}-rx-{image_report_id}",
            "image_report_id": image_report_id,
            "recon_source": recon_drone_id,
            "compute_processor": self.drone_id,
            "received_at": timestamp.isoformat(),
            "location_grid": location_grid,
            "image_quality": image_data.get("quality", 0.85),
            "resolution": image_data.get("resolution", "1080p"),
            "status": "queued-for-processing"
        }
        
        self.image_queue.append(reception_record)
        return reception_record
    
    def process_image(self, image_reception_id: str) -> Dict:
        """
        Process queued image: detect targets, classify, assess threat.
        
        Args:
            image_reception_id: ID of image to process
            
        Returns:
            Processing result with detected targets
        """
        # Find the image in queue
        image = None
        for img in self.image_queue:
            if img["reception_id"] == image_reception_id:
                image = img
                break
        
        if not image:
            return {
                "status": "error",
                "reason": "Image not found in processing queue"
            }
        
        # Simulate image processing with processor capability affecting accuracy
        processing_result = {
            "processing_id": f"{self.drone_id}-proc-{image['image_report_id']}",
            "image_report_id": image["image_report_id"],
            "recon_source": image["recon_source"],
            "compute_processor": self.drone_id,
            "processed_at": datetime.now().isoformat(),
            "location_grid": image["location_grid"],
            "processor_confidence": self.processor_capability,
            "detected_targets": self._simulate_target_detection(image),
            "status": "processed"
        }
        
        self.processed_images[image_reception_id] = processing_result
        self.image_queue.remove(image)  # Remove from processing queue
        
        # Store targets in database for strike decisions
        for target in processing_result["detected_targets"]:
            target_key = f"{image['location_grid']}-{target['target_id']}"
            self.target_database[target_key] = {
                **target,
                "first_detected": datetime.now().isoformat(),
                "processing_id": processing_result["processing_id"]
            }
        
        return processing_result
    
    def _simulate_target_detection(self, image: Dict) -> List[Dict]:
        """
        Simulate AI-powered target detection from image.
        
        Args:
            image: Image reception record
            
        Returns:
            List of detected targets with classification
        """
        import random
        random.seed(hash(image['image_report_id']) % 2**32)
        
        # Detection probability based on processor capability
        detection_count = random.randint(1, 4) if random.random() < self.processor_capability else 0
        
        targets = []
        target_types = [
            TargetType.COMMAND_POST,
            TargetType.ARMOR,
            TargetType.ANTI_AIR,
            TargetType.PERSONNEL,
            TargetType.LOGISTICS
        ]
        
        for i in range(detection_count):
            target_type = random.choice(target_types)
            threat_level = self._assess_threat(target_type)
            
            target = {
                "target_id": f"TGT-{image['location_grid']}-{i+1}",
                "type": target_type.value,
                "threat_level": threat_level.value,
                "confidence": round(random.uniform(0.70, 0.99), 2),
                "position": {
                    "grid": image["location_grid"],
                    "estimated_coords": (
                        random.randint(0, 100),
                        random.randint(0, 100)
                    )
                },
                "size_estimate": random.choice(["point", "small-group", "convoy", "formation"]),
                "movement": random.choice(["stationary", "slow", "moderate", "rapid"]),
                "personnel_estimate": random.randint(5, 200) if target_type == TargetType.PERSONNEL else None
            }
            targets.append(target)
        
        return targets
    
    def _assess_threat(self, target_type: TargetType) -> ThreatLevel:
        """Determine threat level from target type."""
        threat_mapping = {
            TargetType.COMMAND_POST: ThreatLevel.CRITICAL,
            TargetType.ANTI_AIR: ThreatLevel.CRITICAL,
            TargetType.ARMOR: ThreatLevel.HIGH,
            TargetType.LOGISTICS: ThreatLevel.MEDIUM,
            TargetType.PERSONNEL: ThreatLevel.LOW,
            TargetType.INFRASTRUCTURE: ThreatLevel.MEDIUM,
            TargetType.UNKNOWN: ThreatLevel.UNKNOWN,
        }
        return threat_mapping.get(target_type, ThreatLevel.UNKNOWN)
    
    def make_strike_decision(
        self,
        target_key: str,
        soldier_approval: bool = False,
        soldier_priority_override: Optional[int] = None
    ) -> Dict:
        """
        Analyze target and decide whether to authorize strike.
        
        Args:
            target_key: Key to target in database (grid-targetid)
            soldier_approval: Whether soldier has pre-approved this target
            soldier_priority_override: Soldier's priority if overriding compute decision
            
        Returns:
            Strike decision with reasoning
        """
        if target_key not in self.target_database:
            return {
                "decision": AttackDecision.DENIED.value,
                "reason": "Target not found in database"
            }
        
        target = self.target_database[target_key]
        
        # Strike decision logic
        decision = self._evaluate_strike_authorization(target, soldier_approval, soldier_priority_override)
        
        # Record decision
        decision_record = {
            "decision_id": f"{self.drone_id}-dec-{target['target_id']}",
            "compute_processor": self.drone_id,
            "target_id": target["target_id"],
            "target_type": target.get("type"),
            "threat_level": target.get("threat_level"),
            "detection_confidence": target.get("confidence"),
            "decision": decision["decision"],
            "reasoning": decision["reasoning"],
            "soldier_approved": soldier_approval,
            "decided_at": datetime.now().isoformat(),
            "status": "pending-relay"
        }
        
        self.strike_decisions[target_key] = decision_record
        return decision_record
    
    def _evaluate_strike_authorization(
        self, 
        target: Dict, 
        soldier_approval: bool,
        soldier_override: Optional[int]
    ) -> Dict:
        """
        Evaluate whether strike is authorized based on rules and soldier input.
        
        Args:
            target: Target object from database
            soldier_approval: Pre-authorized by soldier
            soldier_override: Soldier's priority level if forcing strike
            
        Returns:
            Decision dict with authorization and reasoning
        """
        threat_value = target.get("threat_level", 0)
        confidence = target.get("confidence", 0.5)
        
        # If soldier has pre-approved and overridden, always authorize
        if soldier_override and soldier_approval:
            return {
                "decision": AttackDecision.AUTHORIZE.value,
                "reasoning": f"Authorized by soldier operator (Priority {soldier_override})"
            }
        
        # Threat-based authorization
        if threat_value >= ThreatLevel.CRITICAL.value:
            if confidence >= 0.85:
                return {
                    "decision": AttackDecision.AUTHORIZE.value,
                    "reasoning": f"Critical threat with {confidence:.0%} confidence"
                }
            else:
                return {
                    "decision": AttackDecision.NEEDS_CLARIFICATION.value,
                    "reasoning": f"Critical threat detected but confidence low ({confidence:.0%}), needs soldier confirmation"
                }
        
        elif threat_value >= ThreatLevel.HIGH.value:
            if confidence >= 0.90:
                return {
                    "decision": AttackDecision.AUTHORIZE.value,
                    "reasoning": f"High threat with high confidence ({confidence:.0%})"
                }
            else:
                return {
                    "decision": AttackDecision.HOLD.value,
                    "reasoning": f"High threat but confidence insufficient ({confidence:.0%})"
                }
        
        elif threat_value >= ThreatLevel.MEDIUM.value:
            if soldier_approval:
                return {
                    "decision": AttackDecision.AUTHORIZE.value,
                    "reasoning": "Medium threat approved by soldier operator"
                }
            else:
                return {
                    "decision": AttackDecision.NEEDS_CLARIFICATION.value,
                    "reasoning": "Medium threat requires soldier authorization"
                }
        
        else:
            return {
                "decision": AttackDecision.DENIED.value,
                "reasoning": f"Threat level too low ({threat_value}) for strike authorization"
            }
    
    def relay_targeting_to_attack(
        self,
        decision_record: Dict,
        assigned_attack_drones: List[str]
    ) -> Dict:
        """
        Relay targeting information and strike authorization to attack drones.
        
        Args:
            decision_record: Strike decision record
            assigned_attack_drones: List of attack drone IDs to receive targeting
            
        Returns:
            Relay confirmation with drone assignments
        """
        if decision_record["decision"] != AttackDecision.AUTHORIZE.value:
            return {
                "status": "relay-rejected",
                "reason": f"Cannot relay non-authorized decisions: {decision_record['decision']}"
            }
        
        relay_record = {
            "relay_id": f"{self.drone_id}-relay-{decision_record['decision_id']}",
            "compute_processor": self.drone_id,
            "target_id": decision_record["target_id"],
            "strike_authorized_at": datetime.now().isoformat(),
            "assigned_attack_drones": assigned_attack_drones,
            "target_priority": "immediate",
            "engagement_rules": "fire-on-authorization",
            "status": "transmitted"
        }
        
        return relay_record
    
    def generate_status_report(self) -> Dict:
        """Generate compute drone status report."""
        return {
            "compute_drone_id": self.drone_id,
            "status": self.status,
            "processor_capability": self.processor_capability,
            "images_queued": len(self.image_queue),
            "images_processed": len(self.processed_images),
            "targets_in_database": len(self.target_database),
            "pending_strike_decisions": len([d for d in self.strike_decisions.values() if d["status"] == "pending-relay"]),
            "report_time": datetime.now().isoformat()
        }
    
    def get_target_summary(self, threat_level_filter: Optional[ThreatLevel] = None) -> List[Dict]:
        """Get summary of all tracked targets, optionally filtered by threat level."""
        targets = list(self.target_database.values())
        
        if threat_level_filter:
            targets = [t for t in targets if t.get("threat_level") >= threat_level_filter.value]
        
        return sorted(targets, key=lambda x: x.get("threat_level", 0), reverse=True)
