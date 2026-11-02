# Lab 0 — Hello Flogo (warm-up, ~10 min, by hand)

Your first Flogo app: a **Timer** trigger that runs a flow every 10 seconds, and a **Log Message** activity that prints
a greeting read from an **app property**.

```
Timer trigger (every 10 s) ──► flow SayHello ──► Log Message: "Hello Sydney Water from Flogo - <time>"
```

| You learn | |
|---|---|
| Create an app, a flow, a trigger | the designer basics |
| App properties | the Flogo equivalent of BWCE module properties: change values per environment without rebuilding |
| Mapper expressions | `string.concat(...)`, `datetime.now()` |
| Run an app | **Run as Executable** from the Flogo app view |

Fast track: [`../solutions/Lab0_HelloFlogo.flogo`](../solutions/Lab0_HelloFlogo.flogo)

## Build it

1. In VS Code **Explorer**, right-click the `lab0` folder → **Create New Flogo App** → name it `HelloFlogo`.
   `HelloFlogo.flogo` opens in the Flogo designer.
2. **APP PROPERTIES** tab → add a property:

   | Name | Type | Value |
   |---|---|---|
   | `Greeting.Message` | String | `Hello Sydney Water from Flogo` |

3. **FLOWS** tab → **Create** → name `SayHello` → **Create**. The flow opens on an empty canvas.
4. In the triggers area on the left of the canvas, add a **Timer Trigger**. In its settings set:

   | Setting | Value |
   |---|---|
   | Scheduler Options | `Timer` |
   | Repeating | `True` |
   | Time Interval | `10` |
   | Interval Unit | `Second` |

5. Click **+** after the trigger → **General → Log Message**. Rename it `LogHello` (click the name).
6. In `LogHello` → **Input** tab → **message**, enter this expression:

   ```
   string.concat($property["Greeting.Message"], " - ", datetime.format(datetime.now(), "YYYY-MM-DD hh:mm:ss"))
   ```

7. Save (`Ctrl+S`).

## Run it

**Flogo** app view (Flogo icon in the Activity Bar) → find `HelloFlogo` → **Run as Executable**.
The terminal shows the app starting, then every 10 seconds:

```
INFO  [flogo.general.activity.log] -  Hello Sydney Water from Flogo - 2026-11-03 01:28:58
INFO  [flogo.general.activity.log] -  Hello Sydney Water from Flogo - 2026-11-03 01:29:08
```

(`datetime.now()` is UTC.) Stop the app with the stop button, or `Ctrl+C` in its terminal.

## Try
- Change `Greeting.Message` in **APP PROPERTIES**, run again — no code change.
- Set **Add Flow Details** on the Log Message to `True` to see the flow name and instance id in each line.
