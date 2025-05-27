# Warum MongoDB AVX-Unterstützung auf der CPU erfordert

Dieses Dokument erklärt, warum MongoDB (ab Version 5.0, insbesondere ab 6.0) AVX-Unterstützung (Advanced Vector Extensions) auf der CPU benötigt und warum dies in Proxmox-Umgebungen zu Problemen führen kann. Es beschreibt die technischen Gründe, die Auswirkungen und die Lösung für Proxmox-VMs.

## Gründe für die AVX-Anforderung

### 1. Leistungsoptimierung
- **AVX (Advanced Vector Extensions)** ist eine Erweiterung des x86-Befehlssatzes, die SIMD-Operationen (Single Instruction, Multiple Data) ermöglicht. Dies erlaubt der CPU, mehrere Datenoperationen gleichzeitig in einem einzigen Befehl zu verarbeiten.
- MongoDB nutzt AVX, um datenintensive Aufgaben wie Aggregationen, Indizes und Verschlüsselungsoperationen effizienter auszuführen. Dies ist besonders wichtig für große Datenbanken oder hohe Workloads.

### 2. Abhängigkeit von Bibliotheken
- MongoDB verwendet externe Bibliotheken (z. B. Intel's Math Kernel Library), die AVX für optimierte Algorithmen voraussetzen. Diese Bibliotheken sind in die Binaries von MongoDB integriert.
- Ohne AVX-Unterstützung können diese Bibliotheken nicht korrekt funktionieren, was zu Inkompatibilitäten oder Abstürzen führt.

### 3. Entwicklungstrend in Software
- Moderne Datenbanken wie MongoDB setzen zunehmend auf erweiterte CPU-Funktionen wie AVX, um wettbewerbsfähige Leistung zu bieten.
- Ältere CPUs ohne AVX (z. B. Intel- oder AMD-Modelle vor ~2011) werden nicht mehr unterstützt, da sie die Anforderungen moderner Workloads nicht erfüllen.

### 4. MongoDB-Versionen
- Ab MongoDB 5.0 (und verstärkt ab 6.0) wurden AVX-optimierte Funktionen in die Standard-Builds integriert, um neue Features wie Zeitreihen-Daten oder verbesserte Analytik zu unterstützen.
- Ältere Versionen (z. B. MongoDB 4.4) hatten diese Anforderung teilweise nicht, sind aber für aktuelle Anwendungen oft veraltet.

## Warum ist das in Proxmox ein Problem?
In Proxmox-VMs ist die AVX-Unterstützung oft nicht standardmäßig aktiviert, aus folgenden Gründen:
- **Standard-CPU-Typ**: Proxmox verwendet standardmäßig den CPU-Typ `kvm64`, der keine erweiterten Funktionen wie AVX oder AVX2 aktiviert, um maximale Kompatibilität mit verschiedenen Hardware-Plattformen zu gewährleisten.
- **Virtuelle CPU**: Die virtuelle CPU in einer VM zeigt nur die vom Hypervisor freigegebenen CPU-Flags. Selbst wenn der Host AVX unterstützt, ist es in der VM nicht verfügbar, wenn der CPU-Typ dies nicht weitergibt.
- **Ältere Hardware**: Wenn der Proxmox-Host eine ältere CPU ohne AVX (z. B. Intel Core 2 Duo oder ältere AMD-Modelle) verwendet, kann die VM AVX nicht nutzen, selbst bei angepasstem CPU-Typ.

## Lösung in Proxmox
Um MongoDB in einer Proxmox-VM lauffähig zu machen, muss die VM so konfiguriert werden, dass sie AVX-Flags von der Host-CPU weitergibt.

### Schritt 1: Prüfen der Host-CPU
Führe auf dem Proxmox-Server folgenden Befehl aus, um die verfügbaren CPU-Flags zu überprüfen:
```bash
root@proxmox-server:~# grep -o 'avx[^ ]*' /proc/cpuinfo
```
**Beispielausgabe**:
```plaintext
avx
avx2
avx512f
avx512dq
avx512cd
avx512bw
avx512vl
avx512_vnni
```
Wenn `avx` oder `avx2` nicht angezeigt wird, ist MongoDB nicht lauffähig.

### Schritt 2: Benutzerdefinierten CPU-Typ definieren
Definiere einen CPU-Typ mit AVX-Unterstützung in Proxmox:

1. Bearbeite die Datei `/etc/pve/virtual-guest/cpu-models.conf`:
   ```bash
   root@proxmox-server:~# nano /etc/pve/virtual-guest/cpu-models.conf
   ```

2. Füge folgenden Inhalt hinzu:
   ```plaintext
   cpu-model: x86-64-v2-AES-AVX
       flags +avx;+avx2;+xsave;+aes;+popcnt;+ssse3;+sse4_1;+sse4_2
       phys-bits host
       hidden 0
       hv-vendor-id proxmox
       reported-model kvm64
   ```

3. Weise der VM den neuen CPU-Typ zu:
   - Bearbeite die VM-Konfiguration in Proxmox (z. B. über die Web-Oberfläche oder `/etc/pve/qemu-server/<VMID>.conf`).
   - Setze `cpu: x86-64-v2-AES-AVX` in der VM-Konfiguration.
   - Beispiel für `/etc/pve/qemu-server/<VMID>.conf`:
     ```plaintext
     cpu: x86-64-v2-AES-AVX
     ```

4. Starte die VM neu, um die Änderungen zu übernehmen:
   ```bash
   qm stop <VMID>
   qm start <VMID>
   ```

## Praktische Auswirkungen
- **Fehlermeldung ohne AVX**: Wenn AVX nicht verfügbar ist, schlägt der Start von MongoDB fehl, oft mit einer Fehlermeldung wie `Illegal instruction` oder Hinweisen auf fehlende CPU-Features.
- **Performance**: Ohne AVX würde MongoDB (falls es überhaupt läuft) auf langsamere Fallback-Methoden zurückgreifen, was die Leistung erheblich beeinträchtigen könnte.
- **Hardwareanforderungen**: AVX ist seit etwa 2011 in den meisten modernen CPUs (Intel Sandy Bridge oder neuer, AMD Bulldozer oder neuer) verfügbar. Ältere Hardware muss möglicherweise auf ältere MongoDB-Versionen (z. B. 4.4) zurückgreifen, die AVX nicht zwingend erfordern.

## Fazit
MongoDB benötigt AVX, um von optimierten Vektoroperationen und modernen Bibliotheken zu profitieren, die die Leistung bei datenintensiven Aufgaben steigern. In Proxmox-Umgebungen ist AVX oft nicht standardmäßig aktiviert, was durch die Anpassung des CPU-Typs korrigiert werden kann, sofern die Host-CPU AVX unterstützt. Dies stellt sicher, dass MongoDB (z. B. für den CMDB-Syncer) korrekt läuft. Für ältere Hardware ohne AVX können ältere MongoDB-Versionen eine Alternative sein, allerdings mit eingeschränkten Features.
