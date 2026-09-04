'use client';

import { Download, Share2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { trackEvent } from '@/lib/analytics';
import type { AtomicClaim } from './types';

type Props = { claim: AtomicClaim };

function wrapText(context: CanvasRenderingContext2D, text: string, maxWidth: number): string[] {
  const words = text.split(/\s+/);
  const lines: string[] = [];
  let line = '';
  for (const word of words) {
    const next = line ? `${line} ${word}` : word;
    if (context.measureText(next).width > maxWidth && line) {
      lines.push(line);
      line = word;
    } else {
      line = next;
    }
  }
  if (line) lines.push(line);
  return lines.slice(0, 5);
}

export default function ShareClaimButton({ claim }: Props) {
  const createImage = async (): Promise<File> => {
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
    context.font = '700 48px Arial';
    wrapText(context, claim.statement, 1050).forEach((line, index) => {
      context.fillText(line, 72, 170 + index * 62);
    });

    const badgeY = 500;
    context.fillStyle = claim.verdict === 'supported' ? '#093e31' : claim.verdict === 'contradicted' ? '#4b1721' : '#263247';
    context.fillRect(72, badgeY, 300, 70);
    context.fillStyle = '#ffffff';
    context.font = '700 28px Arial';
    context.fillText(claim.verdict.toUpperCase(), 96, badgeY + 45);
    context.fillStyle = '#aebed6';
    context.font = '24px Arial';
    context.fillText(`Evidence freshness: ${claim.freshness}`, 410, badgeY + 44);
    context.fillText('Research only · Verify against the linked official evidence', 72, 608);

    const blob = await new Promise<Blob>((resolve, reject) => {
      canvas.toBlob((value) => value ? resolve(value) : reject(new Error('Image generation failed.')), 'image/png');
    });
    return new File([blob], 'fundersai-truth-check.png', { type: 'image/png' });
  };

  const recordShare = (action: 'shared' | 'downloaded') => {
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
    recordShare('downloaded');
  };

  const handleDownload = async () => {
    try {
      downloadImage(await createImage());
    } catch (error) {
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
      console.error('Could not share the image card:', error);
    }
  };

  return (
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
  );
}
