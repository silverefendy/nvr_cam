path = "frontend/src/pages/Storage/index.tsx"
content = open(path, encoding="utf-8").read()

old1 = "                      {['Kamera', 'Mulai', 'Durasi', 'Ukuran', 'Codec', 'Aksi'].map(h => ("
new1 = "                      {['Kamera', 'Mulai', 'Durasi', 'Ukuran', 'Codec', 'Path File', 'Aksi'].map(h => ("

old2 = """                        <td style={{ padding: '10px 14px' }}>
                          <div style={{ display: 'flex', gap: 6 }} onClick={e => e.stopPropagation()}>"""
new2 = """                        <td style={{ padding: '10px 14px', maxWidth: 200 }}>
                          {rec.file_path ? (
                            <span title={rec.file_path} style={{
                              fontSize: 11, color: sub, fontFamily: 'monospace',
                              display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                            }}>
                              {rec.file_path}
                            </span>
                          ) : (
                            <span style={{ fontSize: 11, color: sub }}>-</span>
                          )}
                        </td>
                        <td style={{ padding: '10px 14px' }}>
                          <div style={{ display: 'flex', gap: 6 }} onClick={e => e.stopPropagation()}>"""

if old1 not in content: print("ERROR old1 not found")
elif old2 not in content: print("ERROR old2 not found")
else:
    content = content.replace(old1, new1, 1).replace(old2, new2, 1)
    open(path, "w", encoding="utf-8").write(content)
    print("OK Storage/index.tsx")
