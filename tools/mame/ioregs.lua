-- ioregs.lua - log the TMS34010 video timing registers from MAME
--
--   END_FRAME=300 tunit <set> -rompath ... -video none -sound none \
--         -nothrottle -autoboot_script tools/mame/ioregs.lua
--
-- At the end of every frame, prints HESYNC, HEBLNK, HSBLNK, HTOTAL,
-- VESYNC, VEBLNK, VSBLNK, VTOTAL, DPYCTL and DPYSTRT when any of them
-- changed since the previous frame. MAME's visible area (and so the frames
-- that frames.lua saves) starts at HEBLNK x 2 pixels, VEBLNK lines; the
-- core's raster follows the same registers, so a game whose blanking
-- registers differ from MK's needs another crop in rgbtool.py.
--
-- Copyright (C) 2026 Gm0rk - GPL-3.0-or-later

local last  = tonumber(os.getenv("END_FRAME") or "300")
local names = { "HESYNC", "HEBLNK", "HSBLNK", "HTOTAL", "VESYNC", "VEBLNK",
                "VSBLNK", "VTOTAL", "DPYCTL", "DPYSTRT" }
local frame, prev = 0, ""

-- keep the subscription in a global: a collected subscription unregisters
frame_sub = emu.add_machine_frame_notifier(function()
	frame = frame + 1
	local sp = manager.machine.devices[":maincpu"].spaces["program"]
	local s = ""
	for i, n in ipairs(names) do
		s = s .. string.format("%s=%04X ", n, sp:read_u16(0xC0000000 + (i - 1) * 0x10))
	end
	if s ~= prev then
		print(string.format("frame %5d  %s", frame, s))
		prev = s
	end
	if frame >= last then manager.machine:exit() end
end)
