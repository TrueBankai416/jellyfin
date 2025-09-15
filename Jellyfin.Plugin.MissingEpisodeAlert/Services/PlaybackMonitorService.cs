using System;
using System.Threading.Tasks;
using MediaBrowser.Controller.Entities.TV;
using MediaBrowser.Controller.Library;
using MediaBrowser.Controller.Session;
using MediaBrowser.Model.Session;
using Microsoft.Extensions.Logging;

namespace Jellyfin.Plugin.MissingEpisodeAlert.Services;

/// <summary>
/// Service for monitoring playback events and detecting missing episodes.
/// </summary>
public class PlaybackMonitorService : IDisposable
{
    private readonly ISessionManager _sessionManager;
    private readonly ILibraryManager _libraryManager;
    private readonly MissingEpisodeDetectionService _detectionService;
    private readonly NotificationService _notificationService;
    private readonly ILogger<PlaybackMonitorService> _logger;
    private bool _disposed = false;

    /// <summary>
    /// Initializes a new instance of the <see cref="PlaybackMonitorService"/> class.
    /// </summary>
    /// <param name="sessionManager">The session manager.</param>
    /// <param name="libraryManager">The library manager.</param>
    /// <param name="detectionService">The missing episode detection service.</param>
    /// <param name="notificationService">The notification service.</param>
    /// <param name="logger">The logger.</param>
    public PlaybackMonitorService(
        ISessionManager sessionManager,
        ILibraryManager libraryManager,
        MissingEpisodeDetectionService detectionService,
        NotificationService notificationService,
        ILogger<PlaybackMonitorService> logger)
    {
        _sessionManager = sessionManager;
        _libraryManager = libraryManager;
        _detectionService = detectionService;
        _notificationService = notificationService;
        _logger = logger;

        // Subscribe to playback events
        _sessionManager.PlaybackStopped += OnPlaybackStopped;
        
        _logger.LogInformation("PlaybackMonitorService initialized and listening for playback events");
    }

    private async void OnPlaybackStopped(object? sender, PlaybackStopEventArgs e)
    {
        try
        {
            var config = Plugin.Instance?.Configuration;
            if (config == null || !config.EnablePlugin)
            {
                return;
            }

            // Only check TV episodes if configured
            if (config.CheckOnlyTvShows && e.Item is not Episode)
            {
                return;
            }

            if (e.Item is Episode episode)
            {
                _logger.LogDebug("Episode playback stopped: {EpisodeName} (S{Season}E{Episode})", 
                    episode.Name, episode.ParentIndexNumber, episode.IndexNumber);

                // Check if the episode was played to completion (at least 90%)
                var playedPercentage = e.PlayedToCompletion ? 100 : 
                    (e.PlaybackPositionTicks.HasValue && episode.RunTimeTicks.HasValue && episode.RunTimeTicks > 0) ?
                    (double)e.PlaybackPositionTicks.Value / episode.RunTimeTicks.Value * 100 : 0;

                if (playedPercentage < 90)
                {
                    _logger.LogDebug("Episode was not played to completion ({Percentage:F1}%), skipping missing episode check", playedPercentage);
                    return;
                }

                // Check for missing next episode
                var missingEpisodeInfo = await _detectionService.CheckForMissingNextEpisodeAsync(episode);
                
                if (missingEpisodeInfo != null)
                {
                    _logger.LogInformation("Missing episode detected after playback: {MissingEpisode} in {SeriesName}", 
                        missingEpisodeInfo.MissingEpisodeIdentifier, missingEpisodeInfo.SeriesName);

                    // Send notification to the user
                    await _notificationService.SendMissingEpisodeNotificationAsync(e.Session, missingEpisodeInfo);

                    // TODO: Implement auto-play prevention logic
                    // This would require hooking into the next episode selection logic
                    // which might need to be done at the client level or through session commands
                }
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error handling playback stopped event");
        }
    }

    /// <inheritdoc />
    public void Dispose()
    {
        if (!_disposed)
        {
            _sessionManager.PlaybackStopped -= OnPlaybackStopped;
            _disposed = true;
            _logger.LogInformation("PlaybackMonitorService disposed");
        }
    }
}
