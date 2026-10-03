# gamescope for dual-screen handhelds

**Work in progress. The bottom-screen drawing (the last commit) is untested on
hardware.**

This branch (`dual-screen`) teaches gamescope to use the second panel of a
dual-screen handheld such as the AYN Thor. It is what [PB-OS](https://github.com/project-barry/pb-os)
runs on the Thor, kept here as plain commits on top of upstream gamescope so
other distributions can take what they need.

Layout: upstream `ad2763d` (2026-09-23), then one **pb-os base** commit (the
Qualcomm/MSM gamescope PB-OS ran before this work: MaSi's MSM port plus
PB-OS's fixes), then the dual-screen commits, each on its own. To use the
dual-screen work elsewhere, cherry-pick the commits after the pb-os base; the
first lease commit is the place to start. PB-OS builds this branch as is.

## What is here

1. **Lending the second panel to another program** (from OpenGamingCollective
   and Armada; credited in each commit). Game Mode's gamescope drives the main
   panel and leases the second one:
   - `--lease-connector <name>` leases that connector (plus a CRTC and a
     primary plane) and offers the lease on a socket
     (`GAMESCOPE_LEASE_SOCK`, default `/tmp/gamescope-lease.sock`) and through
     the standard `wp_drm_lease_device_v1` protocol.
   - `--ignore-touch-device <name>` keeps that panel's touchscreen away from
     the main session; it is forwarded to the program holding the lease.
   - A second gamescope started with `--drm-lease-client <socket>` runs its own
     session on the leased panel (a launcher, a keyboard, a dashboard...).
     With `--drm-lease-yield` it steps aside while a `wp_drm_lease_device_v1`
     client (an emulator that draws its own bottom screen) holds the lease.
2. **`GAMESCOPE_FOCUS_BOTTOM_INSET`** (root window property, pixels): an
   on-screen keyboard along the bottom of a screen pushes the focused app up
   instead of covering it.
3. **`GAMESCOPE_BOTTOM_SCREEN`** (window property, 32-bit, non-zero): the main
   gamescope draws that window on the leased panel itself, fitted and turned
   to the panel, and leaves it out of the main output and focus. While such a
   window is mapped, the lease's holder is suspended (as for a
   `wp_drm_lease_device_v1` client); when none is, it gets the panel back.
   `GAMESCOPE_BOTTOM_SCREEN_ORIENTATION` (`normal`, `left`, `right`,
   `upsidedown`) overrides the panel's orientation.

   Any X11 window can be sent there, for example:

   ```
   xprop -id <window> -f GAMESCOPE_BOTTOM_SCREEN 32c -set GAMESCOPE_BOTTOM_SCREEN 1
   ```

## Planned

- Rules that send an emulator's second window (melonDS, Azahar) to the bottom
  screen on their own, so stock emulators get two screens.
- Touch on the bottom panel going to the window shown there.
- Handing the panel back to the lease's holder on request (an overlay such as
  a performance dashboard) and taking it again after.

Also here: the stats pipe reports the game's frame rate (`fps=`) and the
compositor's (`paintfps=`) once a second, for a bottom-screen dashboard.

## Credits

- Kyle Gospodnetich and the OpenGamingCollective, for the original DRM lease
  support; pacoa-kdbg for the leased-plane fix.
- JPyke3 and virtudude ([Armada](https://github.com/armada-os/armada)), for
  `wp_drm_lease_device_v1`, the leased-output compositor and yielding.
- MaSi ([SteamOS-ARM-SM8550](https://github.com/MaSieS4Fun/SteamOS-ARM-SM8550)),
  for the Qualcomm port.
- The rest of gamescope is Valve's; see README.md and LICENSE.
