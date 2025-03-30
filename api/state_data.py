from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class StateData:
    """Data class to hold state demographic information"""
    state_code: str
    state_name: str
    total_population: int
    race_distribution: Dict[str, int]
    ethnicity_distribution: Dict[str, float]
    voting_age_population: int
    median_age: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert the state data to a dictionary"""
        return {
            "state_code": self.state_code,
            "state_name": self.state_name,
            "total_population": self.total_population,
            "race_distribution": self.race_distribution,
            "ethnicity_distribution": self.ethnicity_distribution,
            "voting_age_population": self.voting_age_population,
            "median_age": self.median_age
        } 