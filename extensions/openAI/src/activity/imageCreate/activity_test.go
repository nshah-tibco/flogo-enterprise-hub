/*
 * Copyright © 2023 - 2026. Cloud Software Group, Inc.
 * This file is subject to the license terms contained
 * in the license file that is distributed with this file.
 */
package imageCreate

import (
	"bufio"
	"fmt"
	"os"
	"strings"
	"testing"

	"github.com/project-flogo/core/activity"
	"github.com/project-flogo/core/support/test"
	"github.com/stretchr/testify/assert"
)

func init() {
	loadEnvFile()
}

func loadEnvFile() {
	file, err := os.Open(".env")
	if err != nil {
		return
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		parts := strings.SplitN(line, "=", 2)
		if len(parts) == 2 {
			k, v := strings.TrimSpace(parts[0]), strings.TrimSpace(parts[1])
			if os.Getenv(k) == "" {
				os.Setenv(k, v)
			}
		}
	}
}

func populateSettingsFromEnv() *Settings {
	return &Settings{
		ApiKey:      os.Getenv("OPEN_AI_API_KEY"),
		EndPointURL: os.Getenv("OPENAI_API_ENDPOINT_URL"),
	}
}

func TestRegister(t *testing.T) {
	ref := activity.GetRef(&Activity{})
	act := activity.Get(ref)
	assert.NotNil(t, act)
}

// ----------------------------------------------------------------------------
// Cross-field validation tests (no network).
// ----------------------------------------------------------------------------

func TestValidate_DallE3_RejectsNGreaterThanOne(t *testing.T) {
	s := &Settings{Model: "dall-e-3", NumberOfImages: 2}
	in := &Input{Prompt: "hi"}
	err := validateInput(s, in)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "dall-e-3 only supports numberOfImages=1")
}

func TestValidate_DallE3_RejectsInvalidQuality(t *testing.T) {
	s := &Settings{Model: "dall-e-3", Quality: "high"}
	in := &Input{Prompt: "hi"}
	err := validateInput(s, in)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "dall-e-3 only supports quality")
}

func TestValidate_DallE2_RejectsHd(t *testing.T) {
	s := &Settings{Model: "dall-e-2", Quality: "hd"}
	in := &Input{Prompt: "hi"}
	err := validateInput(s, in)
	assert.Error(t, err)
}

func TestValidate_GPTImage_AcceptsHighQuality(t *testing.T) {
	s := &Settings{Model: "gpt-image-1", Quality: "high"}
	in := &Input{Prompt: "hi"}
	assert.NoError(t, validateInput(s, in))
}

func TestValidate_StyleOnlyForDallE3(t *testing.T) {
	s := &Settings{Model: "gpt-image-1", Style: "vivid"}
	in := &Input{Prompt: "hi"}
	err := validateInput(s, in)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "'style' is only supported by dall-e-3")
}

func TestValidate_ResponseFormatAndOutputFormatMutuallyExclusive(t *testing.T) {
	s := &Settings{Model: "dall-e-3", ResponseFormat: "url", OutputFormat: "png"}
	in := &Input{Prompt: "hi"}
	err := validateInput(s, in)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "mutually exclusive")
}

func TestValidate_ResponseFormatNotAllowedForGPTImage(t *testing.T) {
	s := &Settings{Model: "gpt-image-1", ResponseFormat: "url"}
	in := &Input{Prompt: "hi"}
	err := validateInput(s, in)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "responseFormat is only supported by dall-e-2/dall-e-3")
}

func TestValidate_OutputFormatNotAllowedForDallE(t *testing.T) {
	s := &Settings{Model: "dall-e-3", OutputFormat: "png"}
	in := &Input{Prompt: "hi"}
	err := validateInput(s, in)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "outputFormat is only supported by gpt-image models")
}

func TestValidate_TransparentBackgroundRequiresPngOrWebp(t *testing.T) {
	s := &Settings{Model: "gpt-image-1", Background: "transparent", OutputFormat: "jpeg"}
	in := &Input{Prompt: "hi"}
	err := validateInput(s, in)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "background=transparent requires outputFormat=png|webp")
}

func TestValidate_TransparentBackgroundAllowsPng(t *testing.T) {
	s := &Settings{Model: "gpt-image-1", Background: "transparent", OutputFormat: "png"}
	in := &Input{Prompt: "hi"}
	assert.NoError(t, validateInput(s, in))
}

func TestValidate_BackgroundOnlyForGPTImage(t *testing.T) {
	s := &Settings{Model: "dall-e-3", Background: "transparent"}
	in := &Input{Prompt: "hi"}
	err := validateInput(s, in)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "background is only supported by gpt-image models")
}

func TestValidate_OutputCompressionOnlyForGPTImage(t *testing.T) {
	s := &Settings{Model: "dall-e-3", OutputCompression: 50}
	in := &Input{Prompt: "hi"}
	err := validateInput(s, in)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "outputCompression is only supported by gpt-image models")
}

func TestValidate_OutputCompressionRequiresWebpOrJpeg(t *testing.T) {
	s := &Settings{Model: "gpt-image-1", OutputFormat: "png", OutputCompression: 50}
	in := &Input{Prompt: "hi"}
	err := validateInput(s, in)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "outputCompression only applies when outputFormat=webp|jpeg")
}

func TestValidate_OutputCompressionRangeCheck(t *testing.T) {
	s := &Settings{Model: "gpt-image-1", OutputFormat: "webp", OutputCompression: 150}
	in := &Input{Prompt: "hi"}
	err := validateInput(s, in)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "between 1 and 100")
}

func TestValidate_ModerationOnlyForGPTImage(t *testing.T) {
	s := &Settings{Model: "dall-e-3", Moderation: "low"}
	in := &Input{Prompt: "hi"}
	err := validateInput(s, in)
	assert.Error(t, err)
}

func TestValidate_DallE2_AllowedSize(t *testing.T) {
	assert.NoError(t, validateInput(&Settings{Model: "dall-e-2", Size: "512x512"}, &Input{Prompt: "hi"}))
	assert.Error(t, validateInput(&Settings{Model: "dall-e-2", Size: "1792x1024"}, &Input{Prompt: "hi"}))
}

func TestValidate_DallE3_AllowedSize(t *testing.T) {
	assert.NoError(t, validateInput(&Settings{Model: "dall-e-3", Size: "1792x1024"}, &Input{Prompt: "hi"}))
	assert.Error(t, validateInput(&Settings{Model: "dall-e-3", Size: "512x512"}, &Input{Prompt: "hi"}))
}

func TestValidate_GPTImage_AutoSize(t *testing.T) {
	assert.NoError(t, validateInput(&Settings{Model: "gpt-image-1", Size: "auto"}, &Input{Prompt: "hi"}))
	assert.Error(t, validateInput(&Settings{Model: "dall-e-2", Size: "auto"}, &Input{Prompt: "hi"}))
}

func TestValidate_GPTImage2_ArbitrarySize(t *testing.T) {
	// Valid: divisible by 16, AR within bounds.
	assert.NoError(t, validateInput(&Settings{Model: "gpt-image-2", Size: "1536x864"}, &Input{Prompt: "hi"}))
	// Invalid: not divisible by 16.
	err := validateInput(&Settings{Model: "gpt-image-2", Size: "1500x864"}, &Input{Prompt: "hi"})
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "divisible by 16")
	// Invalid: aspect ratio > 3:1.
	err = validateInput(&Settings{Model: "gpt-image-2", Size: "3200x800"}, &Input{Prompt: "hi"})
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "aspect ratio")
	// Invalid: exceeds max 3840x2160.
	err = validateInput(&Settings{Model: "gpt-image-2", Size: "4096x2160"}, &Input{Prompt: "hi"})
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "maximum")
}

func TestValidate_PromptLengthByModel(t *testing.T) {
	long := strings.Repeat("a", 1500)
	err := validateInput(&Settings{Model: "dall-e-2"}, &Input{Prompt: long})
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "exceeds limit 1000")

	// dall-e-3 accepts 1500.
	assert.NoError(t, validateInput(&Settings{Model: "dall-e-3"}, &Input{Prompt: long}))
}

func TestValidate_UnknownModel(t *testing.T) {
	err := validateInput(&Settings{Model: "bogus-model"}, &Input{Prompt: "hi"})
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "unknown model")
}

// ----------------------------------------------------------------------------
// Integration test (only runs with RUN_INTEGRATION=1 and credentials in .env).
// ----------------------------------------------------------------------------

func TestImageCreate_Integration(t *testing.T) {
	if os.Getenv("RUN_INTEGRATION") != "1" {
		t.Skip("integration tests disabled")
	}

	s := populateSettingsFromEnv()
	if s.ApiKey == "" || s.EndPointURL == "" {
		t.Skip("missing credentials in .env")
	}

	// Build a real activity via New() so the SDK client is wired.
	settings := map[string]interface{}{
		"apiKey":         s.ApiKey,
		"endPointURL":    s.EndPointURL,
		"model":          "dall-e-2",
		"numberOfImages": int64(1),
		"size":           "256x256",
	}
	initCtx := test.NewActivityInitContext(settings, nil)
	a, err := New(initCtx)
	assert.NoError(t, err)

	tc := test.NewActivityContext(a.Metadata())
	tc.SetInput("prompt", "A cute baby sea otter")

	done, err := a.Eval(tc)
	if !done {
		fmt.Println(err)
		assert.Fail(t, "activity failed")
	}
	assert.NoError(t, err)
	assert.True(t, done)
}
