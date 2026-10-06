-- wrlog.lua - log the 34010's writes outside main RAM and VRAM from MAME
--
--   WRLOG=writes.txt WR_FIRST=40 WR_LAST=70 END_FRAME=70 \
--   PRESS="40:IN0:P1 Shoot / Block:5" \
--   tunit <set> -rompath ... -nvram_directory <empty> -video none \
--         -sound none -nothrottle -autoboot_script tools/mame/wrlog.lua
--
-- One line per write to 0x01400000-0x01FFFFFF (bit addresses: CMOS,
-- inputs, palette, DMA, control, sound) for frames WR_FIRST..WR_LAST:
-- frame, line, word address (bit address >> 4), data - the format of the
-- simulator's --wrlog, so the two logs can be lined up write by write. The
-- line is counted in scan periods from the end of the previous frame (the
-- Lua API has no beam position), so it is only roughly the sim's line.
-- PRESS works as in frames.lua.
--
-- Copyright (C) 2026 Gm0rk - GPL-3.0-or-later

local path  = os.getenv("WRLOG") or "writes.txt"
local first = tonumber(os.getenv("WR_FIRST") or "0")
local wlast = tonumber(os.getenv("WR_LAST") or "100")
local last  = tonumber(os.getenv("END_FRAME") or "100")
local press = os.getenv("PRESS") or ""

local out = io.open(path, "w")
local frame = 0

local presses = {}
for item in press:gmatch("[^;]+") do
	local f, port, field, len = item:match("^(%d+):([^:]+):([^:]+):(%d+)$")
	if f then
		presses[#presses + 1] = { first = tonumber(f), port = ":" .. port, field = field, len = tonumber(len) }
	end
end

local scr
for _, s in pairs(manager.machine.screens) do scr = scr or s end
local sp = manager.machine.devices[":maincpu"].spaces["program"]
local scan = scr.scan_period
local t0 = 0.0

-- keep the tap and the subscription in globals: collected ones unregister
wr_tap = sp:install_write_tap(0x01400000, 0x01FFFFFF, "wrlog", function(offset, data, mask)
	if frame >= first and frame <= wlast then
		local line = math.floor((manager.machine.time:as_double() - t0) / scan)
		out:write(string.format("%d %d %07X %04X\n", frame, line, offset >> 4, data))
	end
end)

frame_sub = emu.add_machine_frame_notifier(function()
	frame = frame + 1
	t0 = manager.machine.time:as_double()
	-- a field pressed by any of its entries reads pressed (several entries
	-- may name the same field, e.g. two coins)
	local ports = manager.machine.ioport.ports
	local level = {}
	for _, p in ipairs(presses) do
		local key = p.port .. "|" .. p.field
		local on = frame >= p.first and frame < p.first + p.len
		level[key] = level[key] or { port = p.port, field = p.field, on = false }
		level[key].on = level[key].on or on
	end
	for _, l in pairs(level) do
		local fld = ports[l.port] and ports[l.port].fields[l.field]
		if fld then fld:set_value(l.on and 1 or 0) end
	end
	if frame >= last then
		out:close()
		manager.machine:exit()
	end
end)
