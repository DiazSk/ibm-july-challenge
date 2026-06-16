"use client";

import { useState } from "react";
import BlankPageSolver from "@/components/create/BlankPageSolver";
import CaptionBrief from "@/components/create/CaptionBrief";
import CaptionVariants from "@/components/create/CaptionVariants";
import ImageDirectionCard from "@/components/create/ImageDirectionCard";
import { generateCaptions, generateImagePrompt } from "@/lib/api";
import type { Caption, ImagePromptResult } from "@/lib/types";

export default function CreatePage() {
  const [product, setProduct] = useState("");
  const [occasion, setOccasion] = useState("");
  const [desiredFeel, setDesiredFeel] = useState("");
  const [clusterId, setClusterId] = useState(0);

  const [captions, setCaptions] = useState<Caption[]>([]);
  const [captionLoading, setCaptionLoading] = useState(false);

  const [imageResult, setImageResult] = useState<ImagePromptResult | null>(null);
  const [imageLoading, setImageLoading] = useState(false);

  function handleBlankPageApply(feel: string, cId: number) {
    setDesiredFeel(feel);
    setClusterId(cId);
  }

  async function handleGenerateCaptions() {
    setCaptionLoading(true);
    setCaptions([]);
    setImageResult(null);
    try {
      const result = await generateCaptions({ product, occasion, desired_feel: desiredFeel, cluster_id: clusterId });
      setCaptions(result);
    } catch {
      // silent — user can retry
    } finally {
      setCaptionLoading(false);
    }
  }

  async function handleGenerateImage(caption: string) {
    setImageLoading(true);
    setImageResult(null);
    try {
      const result = await generateImagePrompt(caption, product);
      setImageResult(result);
    } catch {
      // silent
    } finally {
      setImageLoading(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto">
      <BlankPageSolver onApply={handleBlankPageApply} />

      <CaptionBrief
        product={product}
        occasion={occasion}
        desiredFeel={desiredFeel}
        clusterId={clusterId}
        onProductChange={setProduct}
        onOccasionChange={setOccasion}
        onDesiredFeelChange={setDesiredFeel}
        onClusterChange={setClusterId}
        onGenerate={handleGenerateCaptions}
        loading={captionLoading}
      />

      {captions.length > 0 && (
        <CaptionVariants
          captions={captions}
          product={product}
          onGenerateImage={handleGenerateImage}
          imageLoading={imageLoading}
        />
      )}

      {imageResult && <ImageDirectionCard result={imageResult} />}
    </div>
  );
}
