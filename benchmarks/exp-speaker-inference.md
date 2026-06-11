# LLM Speaker-Count Inference Experiment

Gate: only high-confidence predictions would feed pyannote's num_speakers.

| Case | Video | Expected | Predicted | Confidence |
|---|---|---|---|---|
| Me at the zoo - single speaker | Me at the zoo | 1 | None | low |
| music video - should abstain | Rick Astley - Never Gonna Give You Up (Official Vi | None | None | low |
| interview podcast host+guest | Jeff Kaplan: World of Warcraft, Overwatch, Blizzar | 2 | 2 | high |
| single TED speaker | After watching this, your brain will not be the sa | 1 | 1 | high |
| single narrator | The Reason Why Cancer is so Hard to Beat | 1 | 1 | high |
| interview host+guest | Joe Rogan Experience #2217 - Brian Cox | 2 | 2 | high |
| 4-host panel | E15: “The Besties” All-In’s inaugural award show c | 4 | 4 | high |
| music stream - should abstain | lofi hip hop radio - beats to study/relax to 🐾 202 | None | None | low |

- High-confidence predictions: 5/8 (coverage)
- Correct when high-confidence: 5/5 (accuracy@high)
- HARMFUL (high-confidence but wrong): 0
- Abstained appropriately on non-speech: 2/2
