#pragma once
#include "CoreMinimal.h"

class UAnimBlueprint;
class UAnimSequence;
class UAnimGraphNode_Root;
class UEdGraph;

namespace KevinBossAnimation
{
	bool CanAddHealthDeath(UAnimBlueprint* Blueprint, FString& Error);
	bool HasHealthDeathChain(UAnimBlueprint* Blueprint, UAnimSequence* Death, FName Slot);
	bool AddHealthDeath(UAnimBlueprint* Blueprint, UEdGraph* Graph, UAnimSequence* Death, UAnimSequence* Air,
		UAnimGraphNode_Root* Root, FString& Error);
}
