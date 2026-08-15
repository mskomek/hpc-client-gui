# CLI Çıktı Sözleşmesi

> English: [[CLI-Output-Contract]]

Her komut `--format {text,json}` seçeneğine uyar. Aşağıdaki sözleşme
`src/hpc_gui/cli/errors.py` tarafından uygulanır ve kanonik olarak
`docs/cli/exit_codes.md` içinde belgelenir.

## Başarı çıktısı

- **Metin kipi** (öntanımlı): `stdout` üzerinde insan tarafından okunabilir
  sonuçlar.
- **JSON kipi**: `stdout` üzerinde ayrıştırılabilir tek bir nesne.

```bash
hpc-client-gui --format json commands
```

`--quiet` hata dışı çıktıyı bastırır; `--verbose` tanılama ekler. Hiçbiri
çıkış kodunu değiştirmez.

## Hata çıktısı

Hatalar `emit_error` üzerinden yönlendirilir:

- **Metin kipi** — `stderr` üzerinde eyleme dönük bir insan iletisi, altta
  yatan ayrıntı korunarak.
- **JSON kipi** — `stdout` üzerinde tek bir nesne:

```json
{
  "error": {
    "message": "...",
    "exit_code": 1
  }
}
```

## Yinelememe kuralı

Aynı ileti metni asla iki kez yazdırılmaz. Metin kipinde yalnızca `stderr`
üzerinde, JSON kipinde yalnızca `message` alanının içinde görünür. `stdout`
üzerinde JSON tüketen bir ayrıştırıcı aynı iletiyi `stderr` üzerinde de
bulmaz; metin kipinde `stderr` yakalayan bir betik ise `stdout` üzerinde
başıboş bir kopya görmez.

## Çıktıyı tüketme

```bash
if output=$(hpc-client-gui --format json files ls /home/$USER); then
  printf '%s\n' "$output" | jq '.'
else
  status=$?
  printf '%s\n' "$output" | jq -r '.error.message'
  exit "$status"
fi
```

Hata nesnesindeki `exit_code`, sürecin çıkış durumuyla eşleşir; yani her iki
kaynak da kullanılabilir — ancak dallanmak için sürecin çıkış durumu daha
basittir.

## Ayrıca bkz.

[[CLI Çıkış Kodları|CLI-Exit-Codes-TR]] ·
[[CLI Komut Referansı|CLI-Command-Reference-TR]]
