'use client';

import { Download, Share2 } from 'lucide-react';
import { useState } from 'react';
import Image from 'next/image';
import { Button } from '@/components/ui/button';
import { trackEvent } from '@/lib/analytics';
import type { AtomicClaim } from './types';

type Props = { claim: AtomicClaim };

function wrapText(context: CanvasRenderingContext2D, text: string, maxWidth: number, maxLines = 3): string[] {
  const lines: string[] = [];
  let line = '';
  for (const character of text.replace(/\s+/g, ' ')) {
    if (context.measureText(line + character).width > maxWidth && line) {
      if (lines.length === maxLines - 1) {
        lines.push(`${line.slice(0, -2)}…`);
        return lines;
      }
      lines.push(line.trim());
      line = '';
    }
    line += character;
  }
  if (line) lines.push(line);
  return lines;
}

export default function ShareClaimButton({ claim }: Props) {
  const [preview, setPreview] = useState('');
  const [error, setError] = useState('');
  const createImage = async (): Promise<File> => {
    setError('');
    const canvas = document.createElement('canvas');
    canvas.width = 1200;
    canvas.height = 630;
    const context = canvas.getContext('2d');
    if (!context) throw new Error('Canvas is unavailable.');

    const gradient = context.createLinearGradient(0, 0, 1200, 630);
    gradient.addColorStop(0, '#07111f');
    gradient.addColorStop(1, '#14213d');
    context.fillStyle = gradient;
    context.fillRect(0, 0, 1200, 630);

    context.fillStyle = '#00ff9d';
    context.font = '700 28px Arial';
    context.fillText('FUNDERSAI · FUND TRUTH CHECK', 72, 82);
    context.fillStyle = '#ffffff';
    context.font = '700 34px Arial';
    wrapText(context, claim.statement, 1050).forEach((line, index) => {
      context.fillText(line, 72, 170 + index * 44);
    });

    context.font = '700 24px Arial';
    context.fillStyle = '#fcd34d';
    context.fillText('PRIVATE REVIEW · UNAPPROVED', 72, 118);
    context.fillStyle = '#aebed6';
    context.fillText(`Verdict scope: ${(claim.metric || claim.status).replaceAll('_', ' ')} only`, 72, 330);
    const dates = [...new Set(claim.evidence.map((item) => item.as_of_date).filter(Boolean))];
    context.font = '22px Arial';
    context.fillText(`Evidence dates: ${dates.join(', ') || 'Unavailable'}`, 72, 370, 1050);
    const sources = [...new Set(claim.evidence.map((item) => item.source_url).filter(Boolean))];
    wrapText(context, sources.join(' | ') || claim.clarification?.prompt || 'No official evidence attached.', 1050, 2)
      .forEach((line, index) => context.fillText(line, 72, 410 + index * 28));

    const badgeY = 500;
    context.fillStyle = claim.verdict === 'supported' ? '#093e31' : claim.verdict === 'contradicted' ? '#4b1721' : '#263247';
    context.fillRect(72, badgeY, 300, 70);
    context.fillStyle = '#ffffff';
    context.font = '700 28px Arial';
    context.fillText(claim.verdict.toUpperCase(), 96, badgeY + 45);
    context.fillStyle = '#aebed6';
    context.font = '24px Arial';
    context.fillText(`Evidence freshness: ${claim.freshness}`, 410, badgeY + 44);
    context.fillText('Research only · Dates and scope apply · Independently verify the sources', 72, 608);

    const blob = await new Promise<Blob>((resolve, reject) => {
      canvas.toBlob((value) => value ? resolve(value) : reject(new Error('Image generation failed.')), 'image/png');
    });
    setPreview(canvas.toDataURL('image/png'));
    return new File([blob], 'fundersai-truth-check.png', { type: 'image/png' });
  };

  const recordShare = (action: 'shared' | 'download_requested') => {
    trackEvent('fund_truth_check_shared', {
      action,
      metric: claim.metric || 'unknown',
      verdict: claim.verdict,
      freshness: claim.freshness,
    });
  };

  const downloadImage = (file: File) => {
    const url = URL.createObjectURL(file);
    const link = document.createElement('a');
    link.href = url;
    link.download = file.name;
    link.hidden = true;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1_000);
    recordShare('download_requested');
  };

  const handleDownload = async () => {
    try {
      downloadImage(await createImage());
    } catch (error) {
      setError('Image creation failed. Please try again.');
      console.error('Could not create the image card:', error);
    }
  };

  const handleShare = async () => {
    try {
      const file = await createImage();
      if (navigator.share && navigator.canShare?.({ files: [file] })) {
        await navigator.share({ title: 'FundersAI Fund Truth Check', files: [file] });
        recordShare('shared');
        return;
      }
      downloadImage(file);
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return;
      setError('Sharing is unavailable. Use Download image or save the preview.');
      console.error('Could not share the image card:', error);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap justify-end gap-2">
        <Button type="button" variant="outline" size="sm" onClick={handleDownload}>
          <Download />
          Download image
        </Button>
        <Button type="button" variant="outline" size="sm" onClick={handleShare}>
          <Share2 />
          Share image
        </Button>
      </div>
      {error && <p role="alert" className="text-xs text-rose-200">{error}</p>}
      {preview && (
        <figure className="space-y-2">
          <Image src={preview} alt="Private review image with claim scope, verdict, freshness, and evidence dates" width={1200} height={630} unoptimized className="h-auto w-full rounded-lg" />
          <figcaption className="text-xs text-text-3">Image ready. If the download did not start, save this preview using your browser.</figcaption>
        </figure>
      )}
    </div>
  );
}
