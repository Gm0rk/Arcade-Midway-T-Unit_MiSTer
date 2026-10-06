-- region_dump.lua - write every ROM region MAME loaded for the running set
--
--   tunit <set> -rompath ... -video none -sound none \
--         -autoboot_script tools/mame/region_dump.lua
--   (environment: DUMP_DIR, default "regions"; files go to DUMP_DIR/<set>/)
--
-- Region tags lose their leading ':' and ':' becomes '_' ("adpcm:cpu" ->
-- adpcm_cpu.bin). tools/mra_check.py compares these with the MRA streams,
-- independently of the MRA generator's own reading of the driver source.
--
-- Copyright (C) 2026 Gm0rk - GPL-3.0-or-later

local done = false
-- keep the subscription in a global: a collected subscription unregisters
frame_sub = emu.add_machine_frame_notifier(function()
	if done then return end
	done = true
	local dir = (os.getenv("DUMP_DIR") or "regions") .. "/" .. emu.romname()
	os.execute("mkdir -p '" .. dir .. "'")
	for tag, r in pairs(manager.machine.memory.regions) do
		local name = tag:gsub("^:", ""):gsub(":", "_")
		local f = io.open(dir .. "/" .. name .. ".bin", "wb")
		local parts = {}
		local n = r.size
		local chunk = {}
		-- read_u32 follows the region's endianness (the 6809's region is big
		-- endian); write the bytes in region order either way
		local big = (r.endianness == "big")
		for a = 0, n - 1, 4 do
			local v = r:read_u32(a)
			if big then
				chunk[#chunk + 1] = string.char((v >> 24) & 0xff, (v >> 16) & 0xff, (v >> 8) & 0xff, v & 0xff)
			else
				chunk[#chunk + 1] = string.char(v & 0xff, (v >> 8) & 0xff, (v >> 16) & 0xff, (v >> 24) & 0xff)
			end
			if #chunk == 4096 then
				f:write(table.concat(chunk))
				chunk = {}
			end
		end
		f:write(table.concat(chunk))
		f:close()
		print(string.format("%s %X", name, n))
	end
	manager.machine:exit()
end)
