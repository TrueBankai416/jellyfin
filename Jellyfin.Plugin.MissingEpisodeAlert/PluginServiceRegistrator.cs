using System.Threading;
using System.Threading.Tasks;
using MediaBrowser.Controller;
using MediaBrowser.Controller.Plugins;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Jellyfin.Plugin.MissingEpisodeAlert.Services;

namespace Jellyfin.Plugin.MissingEpisodeAlert;

/// <summary>
/// Plugin service registrator for dependency injection.
/// </summary>
public class PluginServiceRegistrator : IPluginServiceRegistrator
{
    /// <inheritdoc />
    public void RegisterServices(IServiceCollection serviceCollection, IServerApplicationHost applicationHost)
    {
        serviceCollection.AddSingleton<MissingEpisodeDetectionService>();
        serviceCollection.AddSingleton<NotificationService>();
        serviceCollection.AddSingleton<PlaybackMonitorService>();
        
        // Use hosted service to ensure PlaybackMonitorService is instantiated
        serviceCollection.AddHostedService<PlaybackMonitorHostedService>();
    }
}

/// <summary>
/// Hosted service that ensures PlaybackMonitorService is instantiated and properly disposed.
/// </summary>
public class PlaybackMonitorHostedService : IHostedService
{
    private readonly PlaybackMonitorService _playbackMonitorService;

    /// <summary>
    /// Initializes a new instance of the <see cref="PlaybackMonitorHostedService"/> class.
    /// </summary>
    /// <param name="playbackMonitorService">The playback monitor service.</param>
    public PlaybackMonitorHostedService(PlaybackMonitorService playbackMonitorService)
    {
        _playbackMonitorService = playbackMonitorService;
    }

    /// <inheritdoc />
    public Task StartAsync(CancellationToken cancellationToken)
    {
        // Service is already instantiated by DI, which triggers event subscription
        return Task.CompletedTask;
    }

    /// <inheritdoc />
    public Task StopAsync(CancellationToken cancellationToken)
    {
        _playbackMonitorService?.Dispose();
        return Task.CompletedTask;
    }
}
