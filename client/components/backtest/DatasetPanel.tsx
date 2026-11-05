import { useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Database, FlaskConical, Upload } from "lucide-react";
import type { DatasetSummary, QualityReport } from "@shared/quant-api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { QuantApiError, quantApi } from "@/lib/quantApi";
import { DATA_KIND_LABELS, fmtDateTime } from "@/lib/format";

export function KindBadge({ kind }: { kind: string }) {
  const synthetic = kind === "synthetic";
  return (
    <Badge
      variant="outline"
      className={
        synthetic
          ? "border-red-300 bg-red-50 text-red-800 dark:bg-red-950 dark:text-red-200"
          : "border-blue-300 bg-blue-50 text-blue-800 dark:bg-blue-950 dark:text-blue-200"
      }
    >
      {DATA_KIND_LABELS[kind] ?? kind}
    </Badge>
  );
}

function QualityIssues({ quality }: { quality: QualityReport }) {
  const shown = quality.issues.filter((i) => i.severity !== "info");
  if (!shown.length) return null;
  return (
    <ul className="space-y-1 text-sm" data-testid="quality-issues">
      {shown.map((i) => (
        <li
          key={`${i.code}-${i.message}`}
          className={i.severity === "error" ? "text-red-700 dark:text-red-300" : "text-amber-700 dark:text-amber-300"}
        >
          <strong>{i.code}</strong> — {i.message}
          {i.rows.length ? ` (lignes ${i.rows.slice(0, 8).join(", ")})` : ""}
        </li>
      ))}
    </ul>
  );
}

interface Props {
  datasets: DatasetSummary[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function DatasetPanel({ datasets, selectedId, onSelect }: Props) {
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const [showImport, setShowImport] = useState(false);
  const [form, setForm] = useState({
    name: "XAUUSD M1",
    symbol: "XAUUSD",
    source: "",
    kind: "historical" as "historical" | "synthetic",
    priceSide: "bid" as "bid" | "mid",
    tzMode: "explicit" as "explicit" | "declared",
    sourceTimezone: "UTC",
  });
  const [rejected, setRejected] = useState<QualityReport | null>(null);

  const refresh = (id: string) => {
    void qc.invalidateQueries({ queryKey: ["datasets"] });
    onSelect(id);
  };

  const demo = useMutation({
    mutationFn: () => quantApi.createDemoDataset(42, 10),
    onSuccess: (r) => refresh(r.dataset.dataset_id),
  });

  const importer = useMutation({
    mutationFn: () => {
      const file = fileRef.current?.files?.[0];
      if (!file) throw new QuantApiError(400, "Choisissez un fichier CSV.");
      if (!form.source.trim()) throw new QuantApiError(400, "Indiquez la source des données (traçabilité).");
      return quantApi.importDataset({
        file,
        filename: file.name,
        name: form.name,
        symbol: form.symbol,
        source: form.source,
        kind: form.kind,
        priceSide: form.priceSide,
        sourceTimezone: form.tzMode === "declared" ? form.sourceTimezone : undefined,
      });
    },
    onMutate: () => setRejected(null),
    onSuccess: (r) => {
      setShowImport(false);
      refresh(r.dataset.dataset_id);
    },
    onError: (e) => {
      const detail = e instanceof QuantApiError ? (e.detail as QualityReport | undefined) : undefined;
      if (detail && Array.isArray(detail.issues)) setRejected(detail);
    },
  });

  const selected = datasets.find((d) => d.dataset_id === selectedId);

  return (
    <Card className="border-border/50">
      <CardHeader>
        <CardTitle className="flex items-center text-base">
          <Database className="mr-2 h-4 w-4" />
          Données
        </CardTitle>
        <CardDescription>Historique validé par le moteur Python (rien n'est corrigé ni comblé).</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {datasets.length === 0 ? (
          <p className="text-sm text-muted-foreground" data-testid="no-dataset">
            Aucun jeu de données. Importez un CSV historique ou générez la démonstration synthétique.
          </p>
        ) : (
          <div className="space-y-2">
            <Label>Jeu de données</Label>
            <Select value={selectedId ?? undefined} onValueChange={onSelect}>
              <SelectTrigger data-testid="dataset-select">
                <SelectValue placeholder="Choisir…" />
              </SelectTrigger>
              <SelectContent>
                {datasets.map((d) => (
                  <SelectItem key={d.dataset_id} value={d.dataset_id}>
                    {d.name} · {d.timeframe} · {d.rows.toLocaleString("fr-FR")} bougies
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {selected && (
              <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                <KindBadge kind={selected.kind} />
                <span>
                  {fmtDateTime(selected.start)} → {fmtDateTime(selected.end)} · source : {selected.source} ·
                  empreinte {selected.dataset_id}
                </span>
              </div>
            )}
          </div>
        )}

        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => demo.mutate()}
            disabled={demo.isPending}
            data-testid="create-demo"
          >
            <FlaskConical className="mr-2 h-4 w-4" />
            {demo.isPending ? "Génération…" : "Générer la démo synthétique"}
          </Button>
          <Button variant="outline" size="sm" onClick={() => setShowImport((v) => !v)}>
            <Upload className="mr-2 h-4 w-4" />
            Importer un CSV
          </Button>
        </div>
        {demo.isError && <p className="text-sm text-red-600">{(demo.error as Error).message}</p>}

        {showImport && (
          <div className="space-y-3 rounded-md border p-3" data-testid="import-form">
            <p className="text-xs text-muted-foreground">
              Colonnes <code>timestamp,open,high,low,close</code> ou export MetaTrader 5. Le fichier est refusé en
              entier en cas d'erreur.
            </p>
            <Input ref={fileRef} type="file" accept=".csv,.txt" aria-label="Fichier CSV" />
            <div className="grid gap-2 sm:grid-cols-3">
              <Input aria-label="Nom" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              <Input
                aria-label="Symbole"
                value={form.symbol}
                onChange={(e) => setForm({ ...form, symbol: e.target.value })}
              />
              <Input
                aria-label="Source"
                placeholder="Source (broker / fournisseur)"
                value={form.source}
                onChange={(e) => setForm({ ...form, source: e.target.value })}
              />
            </div>
            <div className="grid gap-2 sm:grid-cols-3">
              <Select value={form.kind} onValueChange={(v) => setForm({ ...form, kind: v as typeof form.kind })}>
                <SelectTrigger aria-label="Nature des données">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="historical">Historique réel</SelectItem>
                  <SelectItem value="synthetic">Synthétique / démonstration</SelectItem>
                </SelectContent>
              </Select>
              <Select
                value={form.tzMode}
                onValueChange={(v) => setForm({ ...form, tzMode: v as typeof form.tzMode })}
              >
                <SelectTrigger aria-label="Fuseau">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="explicit">Décalage UTC dans le fichier</SelectItem>
                  <SelectItem value="declared">Déclarer le fuseau de la source</SelectItem>
                </SelectContent>
              </Select>
              <Input
                aria-label="Fuseau IANA"
                disabled={form.tzMode !== "declared"}
                value={form.sourceTimezone}
                onChange={(e) => setForm({ ...form, sourceTimezone: e.target.value })}
              />
            </div>
            <Button size="sm" onClick={() => importer.mutate()} disabled={importer.isPending}>
              {importer.isPending ? "Validation…" : "Valider et enregistrer"}
            </Button>
            {importer.isError && (
              <div className="space-y-1">
                <p className="text-sm text-red-600">{(importer.error as Error).message}</p>
                {rejected && <QualityIssues quality={rejected} />}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
