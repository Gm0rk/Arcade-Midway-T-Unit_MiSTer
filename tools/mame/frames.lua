-- frames.lua - reference frames (and optional presses) from MAME
--
--   SNAP_DIR=out SNAP_FRAMES=100,200,300 END_FRAME=300 \
--   PRESS="250:IN1:Coin 1:8;280:IN1:1 Player Start:8" \
--   tunit <set> -rompath ... -video none -sound none -nothrottle \
--         -seconds_to_run 600 -autoboot_script tools/mame/frames.lua
--
-- SNAP_FRAMES   frames to save, comma separated, or "every:N"
-- END_FRAME     last frame to save; MAME exits after it
-- PRESS         frame:port:field:length entries, ';' separated; the field
--               is set at that frame's notification for length frames, and
--               the game sees it from the next notification on (MAME updates
--               its ports in its own frame notifier, which runs before this
--               script's). The simulator's --press with the same numbers
--               presses at that same moment.
--
-- Each saved frame is <SNAP_DIR>/f<frame>.rgb: a 16-byte header ("RGB1",
-- width, height, frame as little-endian 32-bit) and width x height x 3
-- bytes of RGB. Frame n is the picture whose visible area ends at the n-th
-- frame notification after start-up (MAME starts its screen at the start of
-- vertical blank, so that is the n-th whole frame); the simulator saves the
-- same picture as its frame n.
--
-- Getting that picture right takes two corrections. At a frame notification
-- screen:pixels() returns the bitmap of the frame before (MAME has already
-- swapped its two bitmaps), so the file is labelled with that frame's
-- number. And pixels() looks the pens up in the palette as it is now, which
-- for T-Unit games already holds the palette writes the game made in the
-- vertical blank after that frame - colour fades and cycling would show a
-- frame early. So every notification keeps a copy of the palette RAM, and a
-- capture puts the copy from the frame's own notification back for the
-- moment of the lookup, then restores the current colours.
--
-- Copyright (C) 2026 Gm0rk - GPL-3.0-or-later

local dir   = os.getenv("SNAP_DIR") or "frames"
local spec  = os.getenv("SNAP_FRAMES") or "every:60"
local last  = tonumber(os.getenv("END_FRAME") or "600")
local press = os.getenv("PRESS") or ""

os.execute("mkdir -p '" .. dir .. "'")

local want, every = {}, nil
if spec:sub(1, 6) == "every:" then
	every = tonumber(spec:sub(7))
else
	for n in spec:gmatch("%d+") do want[tonumber(n)] = true end
end

local presses = {}
for item in press:gmatch("[^;]+") do
	local f, port, field, len = item:match("^(%d+):([^:]+):([^:]+):(%d+)$")
	if f then
		presses[#presses + 1] = { first = tonumber(f), port = ":" .. port, field = field, len = tonumber(len) }
	end
end

local frame = 0
local function le32(v)
	return string.char(v & 0xff, (v >> 8) & 0xff, (v >> 16) & 0xff, (v >> 24) & 0xff)
end

local scr
for _, sc in pairs(manager.machine.screens) do scr = scr or sc end
local sp = manager.machine.devices[":maincpu"].spaces["program"]

-- palette RAM: 32768 words at bit address 0x01800000
local PAL, NPAL = 0x01800000, 32768
local pal_prev = nil

local function read_palette()
	local p = {}
	for i = 0, NPAL - 1 do p[i] = sp:read_u16(PAL + i * 16) end
	return p
end

local function save(n, pix, w, h)
	local out = {}
	for i = 0, w * h - 1 do
		local a, b, c = pix:byte(i * 4 + 1, i * 4 + 3)
		-- pixels are 32-bit little endian xRGB: bytes B, G, R, x
		out[#out + 1] = string.char(c, b, a)
	end
	local f = io.open(string.format("%s/f%05d.rgb", dir, n), "wb")
	f:write("RGB1" .. le32(w) .. le32(h) .. le32(n))
	f:write(table.concat(out))
	f:close()
end

-- keep the subscription in a global: a collected subscription unregisters
frame_sub = emu.add_machine_frame_notifier(function()
	frame = frame + 1
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

	local n = frame - 1                     -- the frame pixels() holds
	local pal_now = read_palette()
	if n >= 1 and (want[n] or (every and n % every == 0)) then
		local changed = {}
		if pal_prev then
			for i = 0, NPAL - 1 do
				if pal_prev[i] ~= pal_now[i] then
					changed[#changed + 1] = i
					sp:write_u16(PAL + i * 16, pal_prev[i])
				end
			end
		end
		local pix, w, h = scr:pixels()
		for _, i in ipairs(changed) do sp:write_u16(PAL + i * 16, pal_now[i]) end
		save(n, pix, w, h)
	end
	pal_prev = pal_now

	if frame > last then manager.machine:exit() end
end)
