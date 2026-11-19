# Baseline v1

## World
- Map size: 20x20
- Active teams: 2
- Workers per team: 2
- Starting locations: Northwest and Southeast
- Symmetrical, seeded resource distribution

## Survival
- Initial health: 100
- Hunger increase: 10 per update
- Survival update interval: 5
- Hunger increase per update: 10
- Starvation damage: 10
- Leader feeding threshold: 60
- Hunger reduction per berry: 25

## Agent architecture
- Rule-based workers
- Shared team knowledge
- Team storage
- Resource reservations
- Worker surplus-food delivery
- Emergency food withdrawal

## Episode termination
- Leader death eliminates the team
- Workers die upon team elimination
- Workers drop carried resources
- Episode ends when all teams are eliminated

## Initial benchmark seeds
789, 123, 7, 48, 915, 4444