using System;
using System.Collections.Concurrent;
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
    private readonly ConcurrentDictionary<string, Guid> _blockedNextEpisodes = new();
    private bool _disposed;

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
        _sessionManager.PlaybackStart += OnPlaybackStarted;
        
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
                    (e.PlaybackPositionTicks.HasValue && episode.RunTimeTicks.HasValue && episode.RunTimeTicks.Value > 0) ?
                    (double)e.PlaybackPositionTicks.Value / episode.RunTimeTicks.Value * 100 : 0;

                if (playedPercentage < 90)
                {
                    _logger.LogDebug("Episode was not played to completion ({Percentage:F1}%), skipping missing episode check", playedPercentage);
                    return;
                }

                // Check for missing next episode
                var missingEpisodeInfo = await _detectionService.CheckForMissingNextEpisodeAsync(episode).ConfigureAwait(false);
                
                if (missingEpisodeInfo != null)
                {
                    _logger.LogInformation("Missing episode detected after playback: {MissingEpisode} in {SeriesName}", 
                        missingEpisodeInfo.MissingEpisodeIdentifier, missingEpisodeInfo.SeriesName);

                    // Send notification to the user
                    await _notificationService.SendMissingEpisodeNotificationAsync(e.Session, missingEpisodeInfo).ConfigureAwait(false);

                    // Implement auto-play prevention by blocking the next available episode
                    if (config.PreventAutoPlay && missingEpisodeInfo.NextAvailableEpisode != null)
                    {
                        _blockedNextEpisodes[e.Session.Id] = missingEpisodeInfo.NextAvailableEpisode.Id;
                        _logger.LogDebug("Blocked auto-play of next available episode {EpisodeId} for session {SessionId}", 
                            missingEpisodeInfo.NextAvailableEpisode.Id, e.Session.Id);
                    }
                }
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error handling playback stopped event");
        }
    }

    private async void OnPlaybackStarted(object? sender, PlaybackProgressEventArgs e)
    {
        try
        {
            var config = Plugin.Instance?.Configuration;
            if (config == null || !config.EnablePlugin || !config.PreventAutoPlay)
            {
                return;
            }

            // Check if this episode should be blocked
            if (_blockedNextEpisodes.TryRemove(e.Session.Id, out var blockedEpisodeId) && 
                e.Item?.Id == blockedEpisodeId)
            {
                _logger.LogInformation("Stopping auto-play of blocked episode {EpisodeId} for session {SessionId}", 
                    blockedEpisodeId, e.Session.Id);

                // Stop playback immediately
                await _sessionManager.SendPlaystateCommand(e.Session.Id, e.Session.Id, new PlaystateRequest
                {
                    Command = PlaystateCommand.Stop
                }, default).ConfigureAwait(false);
            }
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error handling playback started event");
        }
    }

    /// <inheritdoc />
    public void Dispose()
    {
        if (!_disposed)
        {
            _sessionManager.PlaybackStopped -= OnPlaybackStopped;
            _sessionManager.PlaybackStart -= OnPlaybackStarted;
            _disposed = true;
            _logger.LogInformation("PlaybackMonitorService disposed");
        }
    }
}
