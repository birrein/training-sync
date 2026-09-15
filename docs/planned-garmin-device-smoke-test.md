# Planned Garmin device smoke test

This is an opt-in procedure for a separately authorized live test. It is not
part of the automated suite and must not be run with an active workout that is
already in use. Use a fresh plan key/name and a date that the user explicitly
chooses. The test account, compatible watch/Edge, and device firmware must be
known before starting.

## Evidence levels

1. `training-sync garmin workout preview ...` is offline evidence that the
   domain and adapter produced the intended ordered steps. It proves nothing
   about Garmin Connect or a device.
2. `workout create ... --yes --date ...` is successful only after the template
   and the exact calendar date are read back from Garmin Connect. This proves
   server persistence and calendar identity, not device receipt.
3. The device observation is a separate manual result. Record the device model,
   firmware, Garmin Connect sync time, and what was actually displayed and
   advanced. Do not infer physical behavior from an HTTP success or API
   read-back.

## Fresh test procedure

1. Prepare a new, source-independent JSON plan. Do not use a vault heading,
   completed activity, or an existing planned workout as the test fixture.
2. Run the offline previews for the strength, cycling, and running fixtures.
3. Confirm the previews before authorizing the live mutation. In particular,
   check the complete RDL sequence, the 165-second transition rest, the lateral
   raise combined-side instruction, the cycling power/recovery sequence, and
   the running power range.
4. Create and schedule the fresh template with `--yes`. Read back the workout
   and calendar entry and record their IDs and local date. Stop if any expected
   rest, side instruction, load, termination, target, or context field differs.
5. Trigger normal Garmin Connect synchronization on the compatible device.
   Observe, separately, whether the workout appears, whether the target is
   shown, whether manual/lap advancement works, whether the RDL transition rest
   occurs, whether combined sides are understandable, and whether running
   power/indoor cycling behavior is supported.
6. Record each observation as `observed`, `not observed`, or `not testable`,
   including the device and firmware. A missing device feature is a
   compatibility result, not permission to silently change the prescription.
7. If cleanup is desired, remove the exact test calendar occurrence and/or
   template explicitly after recording the evidence. Verify each removal
   separately; never delete completed activities as cleanup.

Until this procedure succeeds on the target hardware, report only automated
test and Garmin Connect read-back evidence. Actual watch/Edge compatibility,
target display, indoor context, and physical rest/side behavior remain
unverified.
