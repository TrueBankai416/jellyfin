using System;
using System.Threading;
using System.Threading.Tasks;
using MediaBrowser.Controller.Session;
using MediaBrowser.Model.Session;
using Microsoft.Extensions.Logging;

namespace Jellyfin.Plugin.MissingEpisodeAlert.Services;

/// <summary>
/// Service for sending notifications to users about missing episodes.
/// </summary>
public class NotificationService
{
    private readonly ISessionManager _sessionManager;
    private readonly ILogger<NotificationService> _logger;

    /// <summary>
    /// Initializes a new instance of the <see cref="NotificationService"/> class.
    /// </summary>
    /// <param name="sessionManager">The session manager.</param>
    /// <param name="logger">The logger.</param>
    public NotificationService(ISessionManager sessionManager, ILogger<NotificationService> logger)
    {
        _sessionManager = sessionManager;
        _logger = logger;
    }

    /// <summary>
    /// Sends a notification about a missing episode to the user's session.
    /// </summary>
    /// <param name="session">The user session.</param>
    /// <param name="missingEpisodeInfo">Information about the missing episode.</param>
    /// <returns>A task representing the asynchronous operation.</returns>
    public async Task SendMissingEpisodeNotificationAsync(SessionInfo session, MissingEpisodeInfo missingEpisodeInfo)
    {
        try
        {
            var config = Plugin.Instance?.Configuration;
            if (config == null || !config.ShowNotificationPopup)
            {
                return;
            }

            var message = $"Missing Episode Alert: {missingEpisodeInfo.MissingEpisodeIdentifier} of \"{missingEpisodeInfo.SeriesName}\" is missing from your library.";
            
            if (missingEpisodeInfo.NextAvailableEpisode != null)
            {
                var season = missingEpisodeInfo.NextAvailableEpisode.ParentIndexNumber ?? 0;
                var episode = missingEpisodeInfo.NextAvailableEpisode.IndexNumber ?? 0;
                message += $" Next available episode is S{season:D2}E{episode:D2}.";
            }

            var messageCommand = new MessageCommand
            {
                Header = "Missing Episode Alert",
                Text = message,
                TimeoutMs = config.NotificationDurationSeconds * 1000
            };

            await _sessionManager.SendMessageCommand(session.Id, session.UserId.ToString(), messageCommand, CancellationToken.None).ConfigureAwait(false);
            
            _logger.LogInformation("Sent missing episode notification to user {UserId} in session {SessionId}: {Message}", 
                session.UserId, session.Id, message);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error sending missing episode notification to session {SessionId}", session.Id);
        }
    }
}
