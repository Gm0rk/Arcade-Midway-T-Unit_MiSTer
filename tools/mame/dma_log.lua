-- dma_log.lua - log every T-Unit blitter start (registers at the command
-- write) with its frame number, for comparison with the simulator's
-- DMA_TRACE output.
--
--   DMA_LOG=out.txt FIRST=90 LAST=100 [PRESS=...] tunit mk ... \
--     -autoboot_script tools/mame/dma_log.lua
--
-- Copyright (C) 2026 Gm0rk - GPL-3.0-or-later

local out   = io.open(os.getenv("DMA_LOG") or "dma.txt", "w")
local first = tonumber(os.getenv("FIRST") or "0")
local last  = tonumber(os.getenv("LAST") or "100")
local press = os.getenv("PRESS") or ""
local frame = 0
local regs  = {}
for i = 0, 15 do regs[i] = 0 end

local presses = {}
for item in press:gmatch("[^;]+") do
	local f, port, field, len = item:match("^(%d+):([^:]+):([^:]+):(%d+)$")
	if f then presses[#presses + 1] = { first = tonumber(f), port = ":" .. port, field = field, len = tonumber(len) } end
end

local space = manager.machine.devices[":maincpu"].spaces["program"]
dma_tap = space:install_write_tap(0x01a80000, 0x01a800ff, "dmalog", function(offset, data, mask)
	local idx = ((offset - 0x01a80000) >> 4) & 15
	regs[idx] = data
	if idx == 1 and (data & 0x8000) ~= 0 and frame >= first and frame <= last then
		local t = {}
		for i = 0, 15 do t[#t + 1] = string.format("%04X", regs[i]) end
		out:write(string.format("%d %s\n", frame, table.concat(t, " ")))
	end
end)

frame_sub = emu.add_machine_frame_notifier(function()
	frame = frame + 1
	local ports = manager.machine.ioport.ports
	for _, p in ipairs(presses) do
		local fld = ports[p.port] and ports[p.port].fields[p.field]
		if fld then fld:set_value((frame >= p.first and frame < p.first + p.len) and 1 or 0) end
	end
	if frame > last then out:close(); manager.machine:exit() end
end)
