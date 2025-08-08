from dataclasses import dataclass
from typing import List
from infrastructure.command_classification_service import ClassificationExample


@dataclass
class SocialIntentTrainingData:
    """Training data for social intents in dialogue"""

    @staticmethod
    def get_examples() -> List[ClassificationExample]:
        return [
            # Befriend intent (подружиться)
            ClassificationExample("подружиться с барменом", "befriend"),
            ClassificationExample("подружиться с трактирщиком", "befriend"),
            ClassificationExample("подружиться с трактирщицей", "befriend"),
            ClassificationExample("подружиться с официантом", "befriend"),
            ClassificationExample("подружиться с официанткой", "befriend"),
            ClassificationExample("подружиться с хозяином таверны", "befriend"),
            ClassificationExample("подружиться с хозяйкой таверны", "befriend"),
            ClassificationExample("завести дружбу с барменом", "befriend"),
            ClassificationExample("стать другом бармена", "befriend"),
            ClassificationExample("стать друзьями с трактирщиком", "befriend"),
            ClassificationExample("подружиться", "befriend"),
            ClassificationExample("хочу подружиться с тобой", "befriend"),
            ClassificationExample("давай дружить", "befriend"),
            ClassificationExample("стать друзьями", "befriend"),
            ClassificationExample("я хочу, чтобы мы подружились", "befriend"),
            ClassificationExample("давай будем друзьями", "befriend"),
            ClassificationExample("make friends with the innkeeper", "befriend"),
            ClassificationExample("I want to be friends with the bartender", "befriend"),
            ClassificationExample("let's be friends", "befriend"),
        ]