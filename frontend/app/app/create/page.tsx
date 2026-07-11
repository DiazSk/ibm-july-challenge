"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { useQueryClient } from "@tanstack/react-query";
import BlankPageSolver from "@/components/create/BlankPageSolver";
import CaptionBrief from "@/components/create/CaptionBrief";
import CaptionVariants from "@/components/create/CaptionVariants";
import ImageDirectionCard from "@/components/create/ImageDirectionCard";
import ScriptStudio from "@/components/create/ScriptStudio";
import { generateCaptions, generateImagePrompt, saveAsset } from "@/lib/api";
import { useLocalStorage } from "@/lib/useLocalStorage";
import type { Caption, ImagePromptResult } from "@/lib/types";

export default function CreatePage() {
  const queryClient = useQueryClient();

  // Persisted across tab changes and refreshes
  const [product, setProduct, clearProduct] = useLocalStorage("ss_create_product", "");
  const [occasion, setOccasion, clearOccasion] = useLocalStorage("ss_create_occasion", "");
  const [desiredFeel, setDesiredFeel, clearDesiredFeel] = useLocalStorage("ss_create_feel", "");
  const [clusterId, setClusterId, clearClusterId] = useLocalStorage("ss_create_cluster", 0);

  // Ephemeral — reset on tab change (results of the current session)
  const [captions, setCaptions] = useState<Caption[]>([]);
  const [captionLoading, setCaptionLoading] = useState(false);
  const [regenerateLoading, setRegenerateLoading] = useState(false);
  const [allPreviousCaptions, setAllPreviousCaptions] = useState<string[]>([]);
  const [imageResult, setImageResult] = useState<ImagePromptResult | null>(null);
  const [imageLoading, setImageLoading] = useState(false);

  function handleClearBrief() {
    clearProduct();
    clearOccasion();
    clearDesiredFeel();
    clearClusterId();
    setCaptions([]);
    setAllPreviousCaptions([]);
    setImageResult(null);
  }

  function handleBlankPageApply(feel: string, cId: number) {
    setDesiredFeel(feel);
    setClusterId(cId);
  }

  async function handleGenerateCaptions() {
    setCaptionLoading(true);
    setCaptions([]);
    setImageResult(null);
    try {
      const result = await generateCaptions({
        product,
        occasion,
        desired_feel: desiredFeel,
        cluster_id: clusterId,
      });
      setCaptions(result);
      setAllPreviousCaptions(result.map((c) => c.caption));
    } catch {
      // silent — user can retry
    } finally {
      setCaptionLoading(false);
    }
  }

  async function handleRegenerate() {
    setRegenerateLoading(true);
    setImageResult(null);
    try {
      const result = await generateCaptions({
        product,
        occasion,
        desired_feel: desiredFeel,
        cluster_id: clusterId,
        previous_captions: allPreviousCaptions,
      });
      setCaptions(result);
      setAllPreviousCaptions((prev) => [...prev, ...result.map((c) => c.caption)]);
    } catch {
      // silent
    } finally {
      setRegenerateLoading(false);
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

  async function handlePin(caption: string) {
    try {
      await saveAsset({
        asset_type: "caption",
        content: caption,
        cluster_id: clusterId,
        source_tab: "caption_brief",
      });
      queryClient.invalidateQueries({ queryKey: ["workbench"] });
    } catch {
      // silent
    }
  }

  return (
    <motion.div
      className="max-w-2xl mx-auto"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
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
        onClear={handleClearBrief}
        loading={captionLoading}
      />

      {captions.length > 0 && (
        <CaptionVariants
          captions={captions}
          product={product}
          onGenerateImage={handleGenerateImage}
          onRegenerate={handleRegenerate}
          imageLoading={imageLoading}
          regenerateLoading={regenerateLoading}
          onPin={handlePin}
        />
      )}

      {imageResult && <ImageDirectionCard result={imageResult} />}

      <div className="mt-8">
        <ScriptStudio />
      </div>
    </motion.div>
  );
}
