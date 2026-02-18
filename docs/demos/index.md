# logdelve Demo Videos

Step-by-step workflow demonstrations showing how logdelve handles real-world log investigation
scenarios. Each topic walks through a complete use case with short video scenes and explanations.

## Topics

### 1. [You Just Got Paged](you-just-got-paged.md)

Your PagerDuty goes off. Three services are returning 500s. Download the CloudWatch logs,
merge them in logdelve, find the errors, analyze message patterns, trace a failing request
across services, and narrow down the incident time window.

**Scenes**: Open logs -- Get oriented -- Find errors -- Analyze patterns -- Trace request -- Time window

### 2. [What Changed? Baseline Comparison](what-changed.md)

Application latency is up. Compare today's logs against yesterday's baseline to find exactly
what changed: new error patterns, slow queries, frequency spikes. logdelve's anomaly detection
highlights the differences automatically.

**Scenes**: Load baseline -- Spot anomalies -- Analyze changes -- Drill into pattern -- Frequency spikes

### 3. [Post-Mortem Documentation](post-mortem.md)

Investigation is done. Bookmark the key evidence, annotate your findings, save your filter
setup as a reusable session, and export the results for the post-mortem meeting.

**Scenes**: Bookmark evidence -- Annotate findings -- Save session -- Export results

## Recommended Viewing Order

Start with **"You Just Got Paged"** for the full investigation workflow, then explore
**"What Changed?"** for baseline comparison, and finish with **"Post-Mortem"** for documenting
your findings.

## More Ideas

See [promotion-videos.md](../promotion-videos.md) for future video topics.

## Full Documentation

For the complete feature reference, see the [User Guide](../guide.md).
