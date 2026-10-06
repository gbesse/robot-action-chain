# Robot Action Chain

## Français

Outil local pour distinguer l’action **demandée**, l’action **envoyée** après adaptation ou limitation, et l’action **mesurée**. Un changement entre demande et envoi est signalé sans être automatiquement considéré comme un échec ; un écart de suivi au-delà du seuil explicite échoue. Les mesures absentes donnent `inconclusive`. Le rapport contient l’empreinte SHA-256 de la trace.

```sh
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/python -m unittest discover -s tests
.venv/bin/robot-action-chain fixtures/actions.jsonl fixtures/rules.json --locale=fr
```

Chaque ligne JSONL porte `episode`, `step`, les trois actions, leurs horodatages en millisecondes et les unités. Les seuils sont propres à chaque champ dans `fixtures/rules.json`. La fonction Python `record_send(robot, requested, output, episode=..., step=..., units=..., observe=...)` enveloppe un appel explicite à `robot.send_action()` et enregistre la valeur renvoyée par l’adaptateur. `observe` doit fournir une mesure comparable ; elle n’est pas déduite de la commande. Utiliser cette fonction uniquement dans un flux de commande déjà autorisé. L’exemple est synthétique et ne certifie pas la sûreté physique.

Codes de sortie : 0 `pass`, 1 `fail`, 2 entrée invalide, 3 `inconclusive`.

## English

Local tool that separates the **requested**, **sent** (after adapter clipping or modification), and **measured** action. A requested-to-sent change is reported but does not automatically fail; tracking error beyond an explicit threshold does. Missing measurements yield `inconclusive`. The report includes the trace’s SHA-256 hash.

```sh
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/python -m unittest discover -s tests
.venv/bin/robot-action-chain fixtures/actions.jsonl fixtures/rules.json --locale=en
```

Each JSONL line contains `episode`, `step`, three actions, their millisecond timestamps, and units. Thresholds are per field in `fixtures/rules.json`. The Python `record_send(robot, requested, output, episode=..., step=..., units=..., observe=...)` function wraps an explicit `robot.send_action()` call and records the value returned by the adapter. `observe` must supply a comparable measurement; it is not inferred from the command. Use this function only in an already authorized control flow. The sample is synthetic and does not certify physical safety.

Exit codes: 0 `pass`, 1 `fail`, 2 invalid input, 3 `inconclusive`.

## Español

Herramienta local que distingue la acción **solicitada**, la **enviada** tras las modificaciones del adaptador y la **medida**. Un cambio entre solicitud y envío se informa sin considerarlo automáticamente un fallo; un error de seguimiento superior al límite explícito sí falla. Las mediciones ausentes producen `inconclusive`. El informe incluye el hash SHA-256 del registro.

```sh
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/python -m unittest discover -s tests
.venv/bin/robot-action-chain fixtures/actions.jsonl fixtures/rules.json --locale=es
```

Cada línea JSONL contiene `episode`, `step`, las tres acciones, sus marcas de tiempo en milisegundos y las unidades. Los límites se configuran por campo en `fixtures/rules.json`. La función Python `record_send(robot, requested, output, episode=..., step=..., units=..., observe=...)` envuelve una llamada explícita a `robot.send_action()` y registra el valor devuelto por el adaptador. `observe` debe aportar una medición comparable; no se infiere de la orden. Usa esta función solo en un flujo de control ya autorizado. El ejemplo es sintético y no certifica la seguridad física.

Códigos de salida: 0 `pass`, 1 `fail`, 2 entrada no válida, 3 `inconclusive`.

MIT — [LICENSE](LICENSE).
