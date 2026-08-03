package imageCreate

/*
* Copyright © 2023 - 2026. Cloud Software Group, Inc.
* This file is subject to the license terms contained
* in the license file that is distributed with this file.
 */

import (
	"context"
	"errors"
	"fmt"
	"regexp"
	"strconv"
	"strings"

	"github.com/openai/openai-go/v3"
	"github.com/openai/openai-go/v3/option"
	"github.com/project-flogo/core/activity"
	"github.com/project-flogo/core/support/log"
)

var logger = log.ChildLogger(log.RootLogger(), "openAI-image-create-activity")

var activityMd = activity.ToMetadata(&Settings{}, &Input{}, &Output{})

func (a *Activity) Metadata() *activity.Metadata {
	return activityMd
}

func init() {
	_ = activity.Register(&Activity{}, New)
}

// Activity is the OpenAI image-generation activity.
type Activity struct {
	Settings  *Settings
	oaiClient openai.Client
}

// New creates a new instance of the Activity.
func New(ctx activity.InitContext) (activity.Activity, error) {
	s := &Settings{}
	if err := s.FromMap(ctx.Settings()); err != nil {
		return nil, err
	}

	if s.ApiKey == "" {
		return nil, errors.New("validation failed: OpenAI API key is required but not provided in activity settings")
	}
	if s.EndPointURL == "" {
		return nil, errors.New("validation failed: OpenAI endpoint URL is required but not provided in activity settings")
	}

	oaiClient := openai.NewClient(
		option.WithAPIKey(s.ApiKey),
		option.WithBaseURL(s.EndPointURL),
	)

	logger.Infof("OpenAI client initialized for endpoint: %s", s.EndPointURL)

	return &Activity{
		Settings:  s,
		oaiClient: oaiClient,
	}, nil
}

// model family classification
const (
	familyDallE2    = "dall-e-2"
	familyDallE3    = "dall-e-3"
	familyGPTImage  = "gpt-image"
	familyGPTImage2 = "gpt-image-2"
)

func modelFamily(model string) string {
	switch {
	case model == "" || model == "dall-e-2":
		return familyDallE2
	case model == "dall-e-3":
		return familyDallE3
	case strings.HasPrefix(model, "gpt-image-2"):
		return familyGPTImage2
	case strings.HasPrefix(model, "gpt-image"):
		return familyGPTImage
	default:
		return ""
	}
}

// arbitraryWxH matches strings like "1536x864".
var arbitraryWxH = regexp.MustCompile(`^(\d+)x(\d+)$`)

// validateInput enforces the cross-field rules described in the OpenAI
// image-generation API reference.
func validateInput(s *Settings, in *Input) error {
	fam := modelFamily(s.Model)
	if fam == "" {
		return fmt.Errorf("validation failed: unknown model %q", s.Model)
	}

	// Prompt length per model family.
	maxPromptLen := 0
	switch fam {
	case familyDallE2:
		maxPromptLen = 1000
	case familyDallE3:
		maxPromptLen = 4000
	case familyGPTImage, familyGPTImage2:
		maxPromptLen = 32000
	}
	if len(in.Prompt) > maxPromptLen {
		return fmt.Errorf("validation failed: prompt length %d exceeds limit %d for model %q",
			len(in.Prompt), maxPromptLen, s.Model)
	}

	// numberOfImages
	if s.NumberOfImages != 0 {
		if s.NumberOfImages < 1 || s.NumberOfImages > 10 {
			return fmt.Errorf("validation failed: numberOfImages must be between 1 and 10 (got %d)", s.NumberOfImages)
		}
		if fam == familyDallE3 && s.NumberOfImages != 1 {
			return errors.New("validation failed: dall-e-3 only supports numberOfImages=1")
		}
	}

	// quality
	if s.Quality != "" && s.Quality != "auto" {
		switch fam {
		case familyDallE2:
			if s.Quality != "standard" {
				return fmt.Errorf("validation failed: dall-e-2 only supports quality=standard|auto (got %q)", s.Quality)
			}
		case familyDallE3:
			if s.Quality != "standard" && s.Quality != "hd" {
				return fmt.Errorf("validation failed: dall-e-3 only supports quality=standard|hd|auto (got %q)", s.Quality)
			}
		case familyGPTImage, familyGPTImage2:
			if s.Quality != "low" && s.Quality != "medium" && s.Quality != "high" {
				return fmt.Errorf("validation failed: gpt-image models support quality=low|medium|high|auto (got %q)", s.Quality)
			}
		}
	}

	// style — dall-e-3 only
	if s.Style != "" && fam != familyDallE3 {
		return fmt.Errorf("validation failed: 'style' is only supported by dall-e-3 (got model %q)", s.Model)
	}

	// response_format vs output_format mutual exclusivity & model gating
	if s.ResponseFormat != "" && s.OutputFormat != "" {
		return errors.New("validation failed: responseFormat and outputFormat are mutually exclusive")
	}
	if s.ResponseFormat != "" && fam != familyDallE2 && fam != familyDallE3 {
		return fmt.Errorf("validation failed: responseFormat is only supported by dall-e-2/dall-e-3 (got model %q)", s.Model)
	}
	if s.OutputFormat != "" && fam != familyGPTImage && fam != familyGPTImage2 {
		return fmt.Errorf("validation failed: outputFormat is only supported by gpt-image models (got model %q)", s.Model)
	}

	// background — gpt-image only; transparent requires png/webp output
	if s.Background != "" {
		if fam != familyGPTImage && fam != familyGPTImage2 {
			return fmt.Errorf("validation failed: background is only supported by gpt-image models (got model %q)", s.Model)
		}
		if s.Background == "transparent" {
			if s.OutputFormat != "" && s.OutputFormat != "png" && s.OutputFormat != "webp" {
				return fmt.Errorf("validation failed: background=transparent requires outputFormat=png|webp (got %q)", s.OutputFormat)
			}
		}
	}

	// output_compression — gpt-image only, 1-100, only with webp/jpeg.
	// Note: a value of 0 is treated as "not provided" since Flogo's metadata
	// reflection cannot distinguish a missing input from a zero int.
	if s.OutputCompression != 0 {
		if fam != familyGPTImage && fam != familyGPTImage2 {
			return fmt.Errorf("validation failed: outputCompression is only supported by gpt-image models (got model %q)", s.Model)
		}
		if s.OutputCompression < 1 || s.OutputCompression > 100 {
			return fmt.Errorf("validation failed: outputCompression must be between 1 and 100 (got %d)", s.OutputCompression)
		}
		if s.OutputFormat != "" && s.OutputFormat != "webp" && s.OutputFormat != "jpeg" {
			return fmt.Errorf("validation failed: outputCompression only applies when outputFormat=webp|jpeg (got %q)", s.OutputFormat)
		}
	}

	// moderation — gpt-image only
	if s.Moderation != "" && fam != familyGPTImage && fam != familyGPTImage2 {
		return fmt.Errorf("validation failed: moderation is only supported by gpt-image models (got model %q)", s.Model)
	}

	// size
	if err := validateSize(s.Size, fam); err != nil {
		return err
	}

	return nil
}

func validateSize(size, fam string) error {
	if size == "" {
		return nil
	}
	if size == "auto" {
		if fam != familyGPTImage && fam != familyGPTImage2 {
			return fmt.Errorf("validation failed: size=auto is only supported by gpt-image models")
		}
		return nil
	}

	switch fam {
	case familyDallE2:
		switch size {
		case "256x256", "512x512", "1024x1024":
			return nil
		default:
			return fmt.Errorf("validation failed: dall-e-2 supports size 256x256|512x512|1024x1024 (got %q)", size)
		}
	case familyDallE3:
		switch size {
		case "1024x1024", "1792x1024", "1024x1792":
			return nil
		default:
			return fmt.Errorf("validation failed: dall-e-3 supports size 1024x1024|1792x1024|1024x1792 (got %q)", size)
		}
	case familyGPTImage:
		switch size {
		case "1024x1024", "1536x1024", "1024x1536":
			return nil
		default:
			return fmt.Errorf("validation failed: gpt-image supports size 1024x1024|1536x1024|1024x1536|auto (got %q)", size)
		}
	case familyGPTImage2:
		// Standard sizes accepted, plus arbitrary WxH per the model rules.
		switch size {
		case "1024x1024", "1536x1024", "1024x1536":
			return nil
		}
		m := arbitraryWxH.FindStringSubmatch(size)
		if m == nil {
			return fmt.Errorf("validation failed: invalid size %q for gpt-image-2", size)
		}
		w, _ := strconv.Atoi(m[1])
		h, _ := strconv.Atoi(m[2])
		if w%16 != 0 || h%16 != 0 {
			return fmt.Errorf("validation failed: gpt-image-2 size %q must have width and height divisible by 16", size)
		}
		// aspect ratio between 1:3 and 3:1
		if w*3 < h || h*3 < w {
			return fmt.Errorf("validation failed: gpt-image-2 size %q aspect ratio must be between 1:3 and 3:1", size)
		}
		if w > 3840 || h > 2160 {
			return fmt.Errorf("validation failed: gpt-image-2 size %q exceeds maximum 3840x2160", size)
		}
	}
	return nil
}

// Eval executes the activity.
func (a *Activity) Eval(ctx activity.Context) (done bool, err error) {
	in := &Input{}
	if err := ctx.GetInputObject(in); err != nil {
		return false, err
	}

	if strings.TrimSpace(in.Prompt) == "" {
		return false, errors.New("validation failed: prompt is required")
	}
	s := a.Settings
	if err := validateInput(s, in); err != nil {
		return false, err
	}

	logger.Infof("Generating image (model=%q, numberOfImages=%d, size=%q)", s.Model, s.NumberOfImages, s.Size)

	params := openai.ImageGenerateParams{
		Prompt: in.Prompt,
	}
	if s.Model != "" {
		params.Model = openai.ImageModel(s.Model)
	}
	if s.NumberOfImages > 0 {
		params.N = openai.Int(s.NumberOfImages)
	}
	if s.Size != "" {
		params.Size = openai.ImageGenerateParamsSize(s.Size)
	}
	if s.Quality != "" {
		params.Quality = openai.ImageGenerateParamsQuality(s.Quality)
	}
	if s.Style != "" {
		params.Style = openai.ImageGenerateParamsStyle(s.Style)
	}
	if s.ResponseFormat != "" {
		params.ResponseFormat = openai.ImageGenerateParamsResponseFormat(s.ResponseFormat)
	}
	if s.OutputFormat != "" {
		params.OutputFormat = openai.ImageGenerateParamsOutputFormat(s.OutputFormat)
	}
	if s.Background != "" {
		params.Background = openai.ImageGenerateParamsBackground(s.Background)
	}
	if s.OutputCompression != 0 {
		params.OutputCompression = openai.Int(s.OutputCompression)
	}
	if s.Moderation != "" {
		params.Moderation = openai.ImageGenerateParamsModeration(s.Moderation)
	}
	if s.User != "" {
		params.User = openai.String(s.User)
	}

	clientCtx := context.Background()
	resp, err := a.oaiClient.Images.Generate(clientCtx, params)
	if err != nil {
		logger.Errorf("Error generating image: %v", err)
		return false, err
	}

	out := &Output{
		Created:      resp.Created,
		Background:   string(resp.Background),
		OutputFormat: string(resp.OutputFormat),
		Quality:      string(resp.Quality),
		Size:         string(resp.Size),
	}
	for i := range resp.Data {
		out.Data = append(out.Data, &resp.Data[i])
	}
	// Best-effort serialization of usage block (shape is GPT-image specific).
	out.Usage = map[string]interface{}{
		"input_tokens":  resp.Usage.InputTokens,
		"output_tokens": resp.Usage.OutputTokens,
		"total_tokens":  resp.Usage.TotalTokens,
		"input_tokens_details": map[string]interface{}{
			"image_tokens": resp.Usage.InputTokensDetails.ImageTokens,
			"text_tokens":  resp.Usage.InputTokensDetails.TextTokens,
		},
	}

	if err := ctx.SetOutputObject(out); err != nil {
		return false, err
	}
	return true, nil
}
