import dnfile

pe = dnfile.dnPE("/home/dhyanesh/dev/chionecast/downloads/extracted_cast/app/CHIONE-CAST.exe")

def resolve_token(tok):
    table_id = tok >> 24
    row_idx = (tok & 0xFFFFFF) - 1
    if table_id == 0x06:
        if row_idx < len(pe.net.mdtables.MethodDef.rows):
            return "MethodDef::" + str(pe.net.mdtables.MethodDef.rows[row_idx].Name)
    elif table_id == 0x0A:
        if row_idx < len(pe.net.mdtables.MemberRef.rows):
            row = pe.net.mdtables.MemberRef.rows[row_idx]
            cls_name = "?"
            if hasattr(row.Class, "row") and hasattr(row.Class.row, "Name"):
                cls_name = str(row.Class.row.Name)
            elif hasattr(row.Class, "row") and hasattr(row.Class.row, "TypeName"):
                cls_name = str(row.Class.row.TypeName)
            return "MemberRef::" + cls_name + "." + str(row.Name)
    elif table_id == 0x04:
        if row_idx < len(pe.net.mdtables.Field.rows):
            return "FieldDef::" + str(pe.net.mdtables.Field.rows[row_idx].Name)
    elif table_id == 0x01:
        if row_idx < len(pe.net.mdtables.TypeRef.rows):
            return "TypeRef::" + str(pe.net.mdtables.TypeRef.rows[row_idx].TypeName)
    elif table_id == 0x02:
        if row_idx < len(pe.net.mdtables.TypeDef.rows):
            return "TypeDef::" + str(pe.net.mdtables.TypeDef.rows[row_idx].TypeName)
    return f"0x{tok:08X}"

def disassemble_clean(rva, max_len=4000):
    data = pe.get_data(rva, max_len)
    flags = int.from_bytes(data[:2], "little")
    if (flags & 3) == 2:
        code = data[1:1+(flags >> 2)]
    else:
        header_size = (flags >> 12) * 4
        code_size = int.from_bytes(data[4:8], "little")
        code = data[header_size:header_size+code_size]
    
    i = 0
    lines = []
    while i < len(code):
        off = i
        op = code[i]
        i += 1
        if op == 0x72:
            tok = int.from_bytes(code[i:i+4], "little")
            i += 4
            us = pe.net.metadata.streams.get(b"#US")
            try:
                raw = us.get_data_at_offset(tok & 0xFFFFFF, 100)
                decoded_s = raw[1:raw[0]].decode("utf-16le", "ignore")
                lines.append(f"0x{off:04x}: ldstr {repr(decoded_s)}")
            except:
                lines.append(f"0x{off:04x}: ldstr tok 0x{tok:x}")
        elif op == 0x20:
            v = int.from_bytes(code[i:i+4], "little", signed=True)
            i += 4
            lines.append(f"0x{off:04x}: ldc.i4 {v} (0x{v:X})")
        elif op == 0x1f:
            v = code[i]
            i += 1
            lines.append(f"0x{off:04x}: ldc.i4.s {v} (0x{v:X})")
        elif 0x16 <= op <= 0x1e:
            lines.append(f"0x{off:04x}: ldc.i4.{op-0x16}")
        elif op in (0x28, 0x6f):
            tok = int.from_bytes(code[i:i+4], "little")
            i += 4
            lines.append(f"0x{off:04x}: call {resolve_token(tok)}")
        elif op in (0x7b, 0x7d, 0x7c, 0x80):
            tok = int.from_bytes(code[i:i+4], "little")
            i += 4
            opname = {0x7b:"ldfld", 0x7d:"stfld", 0x7c:"ldsfld", 0x80:"stsfld"}[op]
            lines.append(f"0x{off:04x}: {opname} {resolve_token(tok)}")
        elif op == 0x8d:
            tok = int.from_bytes(code[i:i+4], "little")
            i += 4
            lines.append(f"0x{off:04x}: newarr {resolve_token(tok)}")
        elif op == 0x9c:
            lines.append(f"0x{off:04x}: stelem.i1")
        elif op == 0x91:
            lines.append(f"0x{off:04x}: ldelem.u1")
        elif op == 0x25:
            lines.append(f"0x{off:04x}: dup")
        elif op == 0x2a:
            lines.append(f"0x{off:04x}: ret")
        elif op in (0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09):
            lines.append(f"0x{off:04x}: ldloc/ldarg.{op}")
        elif op == 0x0a:
            lines.append(f"0x{off:04x}: stloc.0")
        elif op == 0x0b:
            lines.append(f"0x{off:04x}: stloc.1")
        elif op == 0x0c:
            lines.append(f"0x{off:04x}: stloc.2")
        elif op == 0x0d:
            lines.append(f"0x{off:04x}: stloc.3")
        elif op in (0x2b, 0x2c):
            t = code[i]
            if t >= 128: t -= 256
            i += 1
            lines.append(f"0x{off:04x}: br.s -> 0x{off + 2 + t:04x}")
        elif op == 0x38:
            t = int.from_bytes(code[i:i+4], "little", signed=True)
            i += 4
            lines.append(f"0x{off:04x}: br -> 0x{off + 5 + t:04x}")
        elif op == 0xfe:
            op2 = code[i]
            i += 1
            lines.append(f"0x{off:04x}: fe.{op2:02x}")
        else:
            lines.append(f"0x{off:04x}: op_0x{op:02x}")
    return lines

print("=== USB_LCDrgb565_PrintData MoveNext ===")
for l in disassemble_clean(0x2e8e0):
    print(" ", l)
